from tests.test_vessels import vessel_payload


def calculator_vessel_payload(**overrides):
    payload = vessel_payload(
        sea_consumption=[
            {"mode": "laden", "grade": "MGO", "speed_kt": 12, "consumption_mt_per_day": 24},
            {"mode": "ballast", "grade": "MGO", "speed_kt": 13, "consumption_mt_per_day": 20},
        ],
        port_consumption=[
            {"kind": "port_load", "grade": "MGO", "consumption_mt_per_day": 5},
            {"kind": "port_discharge", "grade": "MGO", "consumption_mt_per_day": 6},
        ],
    )
    payload.update(overrides)
    return payload


def estimate_payload(**overrides):
    """Ust-Luga -> Rotterdam, 1728 NM at 12 kt = 6.000 sea days, 2 + 2 laytime days in port."""
    payload = {
        "name": "UL-RTM June",
        "vessel_id": None,
        "currency": "USD",
        "laycan_start": "2026-06-01",
        "laycan_end": "2026-06-05",
        "freight_mode": "per_mt",
        "sea_mode": "laden",
        "port_charges": 20000,
        "port_stops": [
            {
                "port_name": "Ust-Luga",
                "stop_type": "load",
                "distance_nm": 0,
                "cargo_quantity_mt": 5000,
                "laytime_value": 2,
                "laytime_unit": "days",
            },
            {
                "port_name": "Rotterdam",
                "stop_type": "discharge",
                "distance_nm": 1728,
                "cargo_quantity_mt": 5000,
                "laytime_value": 48,
                "laytime_unit": "hours",
            },
        ],
        "cargo_lots": [{"grade": "gasoil", "quantity_mt": 5000, "freight_rate": 30}],
        "fuel_prices": [{"grade": "MGO", "price_per_mt": 700}],
        "cost_items": [],
    }
    payload.update(overrides)
    return payload


def _vessel_id(client):
    return client.post("/vessels", json=calculator_vessel_payload()).json()["id"]


def test_estimate_calculates_sea_port_time_fuel_and_tce_from_the_vessel_profile(client):
    payload = estimate_payload(vessel_id=_vessel_id(client))

    response = client.post("/voyage-estimates", json=payload)

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "draft"
    results = created["results"]
    assert results["total_distance_nm"] == 1728
    assert results["sea_days"] == 6
    assert results["port_days"] == 4
    assert results["total_voyage_days"] == 10
    # MGO: sea 24*6 + load 5*2 + discharge 6*2 = 166 MT @ 700
    assert results["fuel"]["MGO"] == {"quantity_mt": 166, "cost": 116200}
    assert results["freight_revenue"] == 150000
    # costs = fuel 116200 + port charges 20000; net = 13800; tce = 1380/day
    assert results["total_costs"] == 136200
    assert results["net_result"] == 13800
    assert results["tce_per_day"] == 1380
    assert results["demurrage"] == 0


def test_estimate_without_a_vessel_has_no_sea_time_or_fuel_and_says_so(client):
    response = client.post("/voyage-estimates", json=estimate_payload(extra_sea_days=6))

    results = response.json()["results"]
    assert results["sea_days"] == 6
    assert results["fuel"] == {}
    assert "no_vessel" in results["warnings"]
    assert response.json()["warnings"] == []


def test_port_time_comes_from_the_loading_rate_when_given_and_excess_over_laytime_is_demurrage(client):
    payload = estimate_payload(vessel_id=_vessel_id(client), demurrage_rate=10000)
    payload["port_stops"][1]["rate_mt_per_day"] = 1000  # 5000 MT / 1000 = 5 days vs 2 days laytime

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    assert results["port_days"] == 7
    assert results["allowed_laytime_days"] == 4
    assert results["excess_days"] == 3
    assert results["demurrage"] == 30000


def test_laytime_expressed_as_a_loading_rate_is_converted_to_days(client):
    payload = estimate_payload()
    payload["port_stops"][0].update({"laytime_value": 2500, "laytime_unit": "mt_per_day"})
    payload["port_stops"][1].update({"laytime_value": 250, "laytime_unit": "mt_per_hour"})

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    # load: 5000 / 2500 = 2 days; discharge: 5000 / (250*24) = 0.833 days
    assert results["port_days"] == 2.833


def test_sea_mode_without_consumption_rows_falls_back_to_laden_with_a_warning(client):
    payload = estimate_payload(vessel_id=_vessel_id(client), sea_mode="eco")

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    assert results["effective_sea_mode"] == "laden"
    assert "sea_mode_fallback" in results["warnings"]
    assert results["sea_days"] == 6


def test_ballast_mode_uses_the_ballast_speed_and_consumption(client):
    payload = estimate_payload(vessel_id=_vessel_id(client), sea_mode="ballast")

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    assert results["sea_days"] == 5.538  # 1728 / (13 * 24)
    assert results["effective_sea_mode"] == "ballast"


def test_fuel_grade_spelt_in_cyrillic_merges_with_the_latin_grade_and_price(client):
    vessel = calculator_vessel_payload(
        sea_consumption=[
            {"mode": "laden", "grade": "МГО", "speed_kt": 12, "consumption_mt_per_day": 24},
        ],
    )
    vessel_id = client.post("/vessels", json=vessel).json()["id"]

    results = client.post(
        "/voyage-estimates", json=estimate_payload(vessel_id=vessel_id)
    ).json()["results"]

    assert list(results["fuel"]) == ["MGO"]
    assert results["total_fuel_cost"] == 116200


def test_inerting_consumption_is_burnt_for_the_sea_days_only(client):
    vessel = calculator_vessel_payload(
        port_consumption=[{"kind": "inerting", "grade": "MGO", "consumption_mt_per_day": 2}],
    )
    vessel_id = client.post("/vessels", json=vessel).json()["id"]

    results = client.post(
        "/voyage-estimates", json=estimate_payload(vessel_id=vessel_id)
    ).json()["results"]

    assert results["fuel"]["MGO"]["quantity_mt"] == 144 + 12  # sea 24*6 + inerting 2*6


def test_a_missing_fuel_price_is_flagged_not_silently_priced_at_zero(client):
    payload = estimate_payload(vessel_id=_vessel_id(client), fuel_prices=[])

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    assert "missing_fuel_price:MGO" in results["warnings"]


def test_lumpsum_freight_and_custom_cost_items_feed_the_result(client):
    payload = estimate_payload(
        freight_mode="lumpsum",
        lumpsum_freight=200000,
        cargo_lots=[],
        canal_fees=1000,
        agent_fees=2000,
        bunker_surcharge=3000,
        extra_costs=4000,
        cost_items=[{"description": "Ice pilotage", "amount": 5000}],
    )

    results = client.post("/voyage-estimates", json=payload).json()["results"]

    assert results["freight_revenue"] == 200000
    assert results["extra_items_total"] == 5000
    assert results["other_costs"] == 20000 + 1000 + 2000 + 3000 + 4000 + 5000


def test_per_mt_freight_requires_a_cargo_lot_with_quantity_and_rate(client):
    response = client.post("/voyage-estimates", json=estimate_payload(cargo_lots=[]))

    assert response.status_code == 422


def test_itinerary_is_limited_to_ten_ports_and_must_not_be_empty(client):
    stop = estimate_payload()["port_stops"][0]

    assert client.post("/voyage-estimates", json=estimate_payload(port_stops=[stop] * 11)).status_code == 422
    assert client.post("/voyage-estimates", json=estimate_payload(port_stops=[])).status_code == 422


def test_negative_amounts_are_rejected(client):
    assert client.post("/voyage-estimates", json=estimate_payload(port_charges=-1)).status_code == 422
    payload = estimate_payload()
    payload["port_stops"][1]["distance_nm"] = -5
    assert client.post("/voyage-estimates", json=payload).status_code == 422


def test_estimate_rejects_a_currency_other_than_rub_or_usd(client):
    response = client.post("/voyage-estimates", json=estimate_payload(currency="EUR"))

    assert response.status_code == 422


def test_estimate_rejects_an_unknown_vessel(client):
    response = client.post("/voyage-estimates", json=estimate_payload(vessel_id=999))

    assert response.status_code == 422


def test_calculate_endpoint_returns_results_without_saving(client):
    response = client.post("/voyage-estimates/calculate", json=estimate_payload(vessel_id=_vessel_id(client)))

    assert response.status_code == 200
    assert response.json()["tce_per_day"] == 1380
    assert client.get("/voyage-estimates").json() == []


def test_operator_can_progress_an_estimate_through_negotiation_or_decline_it(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    negotiating = client.post(
        f"/voyage-estimates/{created['id']}/status", json={"status": "under_negotiation"}
    )
    assert negotiating.status_code == 200
    assert negotiating.json()["status"] == "under_negotiation"

    declined = client.post(
        f"/voyage-estimates/{created['id']}/status", json={"status": "declined"}
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"


def _promote(client, estimate_id):
    return client.post(
        f"/voyage-estimates/{estimate_id}/promote",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 30,
            "freight_rate_basis": "per_tonne",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "cargo_grade": "gasoil",
        },
    )


def test_promoting_an_estimate_creates_a_linked_fixture_and_freezes_the_baseline(client):
    vessel_id = _vessel_id(client)
    created = client.post("/voyage-estimates", json=estimate_payload(vessel_id=vessel_id)).json()

    response = _promote(client, created["id"])

    assert response.status_code == 201
    fixture = response.json()
    updated = client.get(f"/voyage-estimates/{created['id']}").json()
    assert updated["status"] == "fixed"
    assert updated["fixture_id"] == fixture["id"]
    assert updated["baseline_net_result"] == 13800
    assert updated["baseline_tce_per_day"] == 1380


def test_editing_the_vessel_profile_later_does_not_move_a_fixed_estimates_baseline(client):
    vessel_id = _vessel_id(client)
    created = client.post("/voyage-estimates", json=estimate_payload(vessel_id=vessel_id)).json()
    _promote(client, created["id"])

    cheaper = calculator_vessel_payload(
        sea_consumption=[
            {"mode": "laden", "grade": "MGO", "speed_kt": 12, "consumption_mt_per_day": 1},
        ],
    )
    client.put(f"/vessels/{vessel_id}", json=cheaper)

    fixed = client.get(f"/voyage-estimates/{created['id']}").json()
    assert fixed["baseline_net_result"] == 13800


def test_a_fixed_estimate_cannot_be_edited_or_deleted(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()
    _promote(client, created["id"])

    assert client.put(f"/voyage-estimates/{created['id']}", json=estimate_payload()).status_code == 409
    assert client.delete(f"/voyage-estimates/{created['id']}").status_code == 409


def test_operator_can_list_and_retrieve_voyage_estimates(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    list_response = client.get("/voyage-estimates")
    assert list_response.status_code == 200
    assert any(e["id"] == created["id"] for e in list_response.json())

    fetched = client.get(f"/voyage-estimates/{created['id']}").json()
    assert fetched["name"] == "UL-RTM June"
    assert [s["port_name"] for s in fetched["port_stops"]] == ["Ust-Luga", "Rotterdam"]
    assert fetched["fuel_prices"][0]["grade"] == "MGO"


def test_operator_can_correct_an_estimate_and_its_results_update(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    revised = estimate_payload(cargo_lots=[{"grade": "gasoil", "quantity_mt": 5000, "freight_rate": 35}])
    response = client.put(f"/voyage-estimates/{created['id']}", json=revised)

    assert response.status_code == 200
    updated = response.json()
    assert updated["cargo_lots"][0]["freight_rate"] == 35
    assert updated["results"]["freight_revenue"] == 175000
    assert len(updated["port_stops"]) == 2


def test_correcting_an_estimate_preserves_its_status_and_fixture_link(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()
    client.post(f"/voyage-estimates/{created['id']}/status", json={"status": "under_negotiation"})

    response = client.put(f"/voyage-estimates/{created['id']}", json=estimate_payload(port_charges=1))

    assert response.status_code == 200
    assert response.json()["status"] == "under_negotiation"
    assert response.json()["fixture_id"] is None


def test_correcting_an_unknown_estimate_returns_404(client):
    response = client.put("/voyage-estimates/999999", json=estimate_payload())

    assert response.status_code == 404


def test_operator_can_delete_an_unfixed_estimate(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    assert client.delete(f"/voyage-estimates/{created['id']}").status_code == 204
    assert client.get(f"/voyage-estimates/{created['id']}").status_code == 404


def test_a_vessel_with_an_estimate_cannot_be_deleted(client):
    vessel_id = _vessel_id(client)
    client.post("/voyage-estimates", json=estimate_payload(vessel_id=vessel_id))

    assert client.delete(f"/vessels/{vessel_id}").status_code == 409


def test_vessel_update_without_a_calculator_profile_leaves_it_untouched(client):
    vessel_id = _vessel_id(client)

    plain = vessel_payload(name="Renamed")
    client.put(f"/vessels/{vessel_id}", json=plain)

    fetched = client.get(f"/vessels/{vessel_id}").json()
    assert fetched["name"] == "Renamed"
    assert len(fetched["sea_consumption"]) == 2
    assert len(fetched["port_consumption"]) == 2


def test_vessel_calculator_profile_rejects_an_impossible_speed(client):
    bad = calculator_vessel_payload(
        sea_consumption=[
            {"mode": "laden", "grade": "MGO", "speed_kt": 0, "consumption_mt_per_day": 24},
        ]
    )

    assert client.post("/vessels", json=bad).status_code == 422


def test_port_list_supports_add_list_duplicate_rejection_and_delete(client):
    created = client.post("/ports", json={"name": "Ust-Luga"})
    assert created.status_code == 201
    assert client.post("/ports", json={"name": "Ust-Luga"}).status_code == 409
    client.post("/ports", json={"name": "Archangelsk"})

    assert [p["name"] for p in client.get("/ports").json()] == ["Archangelsk", "Ust-Luga"]
    assert client.delete(f"/ports/{created.json()['id']}").status_code == 204
    assert [p["name"] for p in client.get("/ports").json()] == ["Archangelsk"]
