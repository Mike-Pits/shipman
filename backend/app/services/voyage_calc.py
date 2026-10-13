"""Preliminary voyage (TCE) calculation engine.

Originated in the standalone `voyage-calculator.html`. Pure functions over duck-typed inputs: the
`estimate` argument and its children may be a Pydantic payload or an ORM row. Speed and fuel
consumption come from the vessel's profile on the Vessels page:

- each itinerary leg is sailed in its own condition (laden / ballast) at that condition's speed,
  burning that condition's IFO and MGO per day;
- time in a loading port burns the vessel's idle/anchor rate, in a discharge port the discharging
  rate; extra sea days burn the laden rate.

Day figures in the result are rounded to 3 decimals for display; intermediates are unrounded.
"""

from app.services.flexible_datetime import round_days

FUEL_GRADES = ("IFO", "MGO")
# Which vessel profile mode a stop's port time burns.
PORT_MODE = {"load": "idle_anchor", "discharge": "discharging"}


def _n(value) -> float:
    return float(value) if value is not None else 0.0


def laytime_days(stop) -> float:
    value = _n(stop.laytime_value)
    unit = stop.laytime_unit
    if unit == "hours":
        return value / 24
    if unit == "days":
        return value
    if unit == "mt_per_hour":
        return _n(stop.cargo_quantity_mt) / (value * 24) if value > 0 else 0.0
    if unit == "mt_per_day":
        return _n(stop.cargo_quantity_mt) / value if value > 0 else 0.0
    return 0.0


def port_days(stop) -> float:
    rate = _n(stop.rate_mt_per_day)
    if rate > 0:
        return _n(stop.cargo_quantity_mt) / rate
    return laytime_days(stop)


def calculate_voyage(estimate, vessel) -> dict:
    """`vessel` may be None (estimate before a vessel is assigned): no sea time or fuel is computed."""
    stops = list(estimate.port_stops)
    profiles = {p.mode: p for p in vessel.fuel_consumption_profiles} if vessel is not None else {}
    warnings: list[str] = []
    fuel_qty = {grade: 0.0 for grade in FUEL_GRADES}

    def burn(mode: str, days: float) -> None:
        profile = profiles.get(mode)
        if profile is None:
            if vessel is not None and days > 0:
                warning = f"missing_profile:{mode}"
                if warning not in warnings:
                    warnings.append(warning)
            return
        fuel_qty["IFO"] += _n(profile.ifo_mt_per_day) * days
        fuel_qty["MGO"] += _n(profile.mgo_mt_per_day) * days

    total_distance = 0.0
    leg_days = {"laden": 0.0, "ballast": 0.0}
    for stop in stops:
        distance = _n(stop.distance_nm)
        total_distance += distance
        if distance <= 0 or vessel is None:
            continue
        profile = profiles.get(stop.condition)
        speed = _n(profile.speed_kt) if profile is not None else 0.0
        if speed <= 0:
            warning = f"missing_speed:{stop.condition}"
            if warning not in warnings:
                warnings.append(warning)
            continue
        # Knots are nautical miles per hour: distance / speed = hours.
        days = distance / (speed * 24)
        leg_days[stop.condition] += days
        burn(stop.condition, days)

    extra_days = _n(estimate.extra_sea_days)
    if vessel is not None:
        burn("laden", extra_days)
    sea_days = leg_days["laden"] + leg_days["ballast"] + extra_days

    stop_days = [(s, port_days(s)) for s in stops]
    total_port_days = sum(d for _, d in stop_days)
    load_days = sum(d for s, d in stop_days if s.stop_type == "load")
    discharge_days = sum(d for s, d in stop_days if s.stop_type != "load")
    if vessel is not None:
        for stop, days in stop_days:
            burn(PORT_MODE.get(stop.stop_type, "discharging"), days)
    total_days = sea_days + total_port_days

    prices = {p.grade: _n(p.price_per_mt) for p in estimate.fuel_prices}
    fuel = {}
    total_fuel_cost = 0.0
    for grade, qty in fuel_qty.items():
        if qty <= 0:
            continue
        if grade not in prices:
            warnings.append(f"missing_fuel_price:{grade}")
        cost = qty * prices.get(grade, 0.0)
        fuel[grade] = {"quantity_mt": round(qty, 3), "cost": round(cost, 2)}
        total_fuel_cost += cost

    if estimate.freight_mode == "lumpsum":
        freight = _n(estimate.lumpsum_freight)
    else:
        freight = sum(_n(l.quantity_mt) * _n(l.freight_rate) for l in estimate.cargo_lots)

    extra_items = sum(_n(i.amount) for i in estimate.cost_items)
    other_costs = (
        _n(estimate.canal_fees) + _n(estimate.port_charges) + _n(estimate.agent_fees)
        + _n(estimate.bunker_surcharge) + _n(estimate.extra_costs) + extra_items
    )

    allowed = sum(laytime_days(s) for s in stops if _n(s.laytime_value) > 0)
    excess = max(0.0, total_port_days - allowed)
    demurrage = excess * _n(estimate.demurrage_rate)

    total_costs = total_fuel_cost + other_costs + demurrage
    net = freight - total_costs
    tce = net / total_days if total_days > 0 else 0.0

    if vessel is None:
        warnings.insert(0, "no_vessel")

    return {
        "total_distance_nm": round(total_distance, 1),
        "sea_days": round_days(sea_days),
        "sea_laden_days": round_days(leg_days["laden"]),
        "sea_ballast_days": round_days(leg_days["ballast"]),
        "port_days": round_days(total_port_days),
        "load_days": round_days(load_days),
        "discharge_days": round_days(discharge_days),
        "total_voyage_days": round_days(total_days),
        "fuel": fuel,
        "total_fuel_cost": round(total_fuel_cost, 2),
        "freight_revenue": round(freight, 2),
        "other_costs": round(other_costs, 2),
        "extra_items_total": round(extra_items, 2),
        "allowed_laytime_days": round_days(allowed),
        "excess_days": round_days(excess),
        "demurrage": round(demurrage, 2),
        "total_costs": round(total_costs, 2),
        "net_result": round(net, 2),
        "tce_per_day": round(tce, 2),
        "warnings": warnings,
    }
