"""Preliminary voyage (TCE) calculation engine.

Ported from the standalone `voyage-calculator.html`. Pure functions over duck-typed inputs: the
`estimate` argument and its children may be a Pydantic payload or an ORM row — only the attributes
read below are required. Day figures in the result are rounded to 3 decimals for display; every
intermediate is unrounded.
"""

from collections import defaultdict

from app.services.flexible_datetime import round_days
from app.services.fuel_grades import normalize_grade

SEA_MODES = ("laden", "ballast", "eco")


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
    total_distance = sum(_n(s.distance_nm) for s in stops)

    sea_rows = []
    effective_mode = estimate.sea_mode
    if vessel is not None:
        sea_rows = [r for r in vessel.sea_consumption if r.mode == estimate.sea_mode]
        if not sea_rows:
            sea_rows = [r for r in vessel.sea_consumption if r.mode == "laden"]
            effective_mode = "laden"
    speed = _n(sea_rows[0].speed_kt) if sea_rows else 0.0
    # Knots are nautical miles per hour: distance / speed = hours.
    sea_days = (total_distance / (speed * 24) if speed > 0 else 0.0) + _n(estimate.extra_sea_days)

    stop_days = [(s, port_days(s)) for s in stops]
    total_port_days = sum(d for _, d in stop_days)
    total_days = sea_days + total_port_days

    fuel_qty: dict[str, float] = defaultdict(float)
    load_days = discharge_days = 0.0
    if vessel is not None:
        port_rows = defaultdict(list)
        for row in vessel.port_consumption:
            port_rows[row.kind].append(row)
        for row in sea_rows:
            fuel_qty[normalize_grade(row.grade)] += _n(row.consumption_mt_per_day) * sea_days
        for stop, days in stop_days:
            kind = "port_load" if stop.stop_type == "load" else "port_discharge"
            for row in port_rows[kind]:
                fuel_qty[normalize_grade(row.grade)] += _n(row.consumption_mt_per_day) * days
        for row in port_rows["inerting"]:
            fuel_qty[normalize_grade(row.grade)] += _n(row.consumption_mt_per_day) * sea_days
    for stop, days in stop_days:
        if stop.stop_type == "load":
            load_days += days
        else:
            discharge_days += days

    prices = {normalize_grade(p.grade): _n(p.price_per_mt) for p in estimate.fuel_prices}
    fuel = {}
    total_fuel_cost = 0.0
    missing_prices = []
    for grade, qty in fuel_qty.items():
        if not grade:
            continue
        if grade not in prices:
            missing_prices.append(grade)
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

    warnings = []
    if vessel is None:
        warnings.append("no_vessel")
    elif effective_mode != estimate.sea_mode:
        warnings.append("sea_mode_fallback")
    for grade in missing_prices:
        warnings.append(f"missing_fuel_price:{grade}")

    return {
        "total_distance_nm": round(total_distance, 1),
        "sea_days": round_days(sea_days),
        "port_days": round_days(total_port_days),
        "load_days": round_days(load_days),
        "discharge_days": round_days(discharge_days),
        "total_voyage_days": round_days(total_days),
        "effective_sea_mode": effective_mode,
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
