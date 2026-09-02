from tests.test_vessels import vessel_payload


def _create_vessel_and_laden_voyage(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 25.0,
            "freight_rate_basis": "per_tonne",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "cargo_grade": "gasoil",
        },
    ).json()["id"]
    voyage_id = client.post(
        "/voyages",
        json={
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "voyage_number": "V-001",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "start_date": "2026-05-27",
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    ).json()["id"]
    return vessel_id, voyage_id


def _submit_report(client, vessel_id, voyage_id, date_code, rob_ifo, rob_mgo):
    text = f"1 {date_code}/0800\n31 {rob_ifo}/{rob_mgo}\nNNNN"
    return client.post(
        "/daily-reports", json={"vessel_id": vessel_id, "voyage_id": voyage_id, "raw_text": text}
    ).json()


def test_first_report_for_a_vessel_has_no_warnings_with_nothing_to_compare_against(client):
    vessel_id, voyage_id = _create_vessel_and_laden_voyage(client)

    report = _submit_report(client, vessel_id, voyage_id, "2705", "232,26", "46,108")

    assert report["warnings"] == []


def test_normal_consumption_produces_no_warning(client):
    vessel_id, voyage_id = _create_vessel_and_laden_voyage(client)
    _submit_report(client, vessel_id, voyage_id, "2705", "232,26", "46,108")

    # vessel_payload's laden profile: 18.5 IFO/day, 0.5 MGO/day -> well within 20%
    report = _submit_report(client, vessel_id, voyage_id, "2805", "214,26", "45,708")

    assert report["warnings"] == []


def test_excess_consumption_with_no_replenishment_produces_a_warning(client):
    vessel_id, voyage_id = _create_vessel_and_laden_voyage(client)
    _submit_report(client, vessel_id, voyage_id, "2705", "232,26", "46,108")

    # IFO consumption of 30 MT vs. a normal rate of 18.5 MT/day (threshold 22.2) -> warning
    report = _submit_report(client, vessel_id, voyage_id, "2805", "202,26", "45,708")

    assert len(report["warnings"]) == 1
    assert "IFO" in report["warnings"][0]


def test_a_recent_bunker_replenishment_suppresses_the_warning_for_that_grade(client):
    vessel_id, voyage_id = _create_vessel_and_laden_voyage(client)
    _submit_report(client, vessel_id, voyage_id, "2705", "232,26", "46,108")
    client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-05-28 02:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 50, "price_per_mt": 550}],
        },
    )

    report = _submit_report(client, vessel_id, voyage_id, "2805", "202,26", "45,708")

    assert report["warnings"] == []
