from tests.test_vessels import vessel_payload


def _create_tc_out_voyage(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "time_charter_out",
            "charterer": "Northern Charterers Ltd",
            "contract_currency": "USD",
            "hire_rate": 9000,
            "hire_rate_basis": "daily",
            "charter_period_from": "2026-06-01",
            "charter_period_to": "2026-08-30",
            "hire_payment_basis": "advance",
            "hire_payment_frequency_days": 30,
        },
    ).json()["id"]
    voyage_id = client.post(
        "/voyages",
        json={
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "voyage_number": "TC-001",
            "load_port": "Ust-Luga",
            "discharge_port": "Ust-Luga",
            "start_date": "2026-06-01",
            "end_date": "2026-08-30",
            "cargo_grade": "n/a",
            "cargo_quantity_mt": 0,
            "laden": False,
        },
    ).json()["id"]
    return voyage_id


def _create_voyage_charter_voyage(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 25.0,
            "freight_rate_basis": "per_tonne",
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
            "start_date": "2026-06-01",
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    ).json()["id"]
    return voyage_id


def test_off_hire_deduction_is_calculated_automatically_from_dates_and_hire_rate(client):
    voyage_id = _create_tc_out_voyage(client)

    response = client.post(
        f"/voyages/{voyage_id}/off-hire-periods",
        json={
            "start_datetime": "2026-06-05 00:00:00",
            "end_datetime": "2026-06-07 00:00:00",
            "reason": "Main engine breakdown",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["duration_days"] == 2
    assert created["calculated_deduction"] == 18000
    assert created["effective_deduction"] == 18000


def test_operator_can_override_the_calculated_deduction(client):
    voyage_id = _create_tc_out_voyage(client)

    response = client.post(
        f"/voyages/{voyage_id}/off-hire-periods",
        json={
            "start_datetime": "2026-06-05 00:00:00",
            "end_datetime": "2026-06-07 00:00:00",
            "reason": "Partial off-hire clause applies",
            "override_deduction": 15000,
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["calculated_deduction"] == 18000
    assert created["effective_deduction"] == 15000


def test_off_hire_is_rejected_for_a_non_tc_out_voyage(client):
    voyage_id = _create_voyage_charter_voyage(client)

    response = client.post(
        f"/voyages/{voyage_id}/off-hire-periods",
        json={
            "start_datetime": "2026-06-05 00:00:00",
            "end_datetime": "2026-06-07 00:00:00",
            "reason": "n/a",
        },
    )

    assert response.status_code == 422


def test_operator_can_list_off_hire_periods_for_a_voyage(client):
    voyage_id = _create_tc_out_voyage(client)
    client.post(
        f"/voyages/{voyage_id}/off-hire-periods",
        json={
            "start_datetime": "2026-06-05 00:00:00",
            "end_datetime": "2026-06-07 00:00:00",
            "reason": "Main engine breakdown",
        },
    )

    response = client.get(f"/voyages/{voyage_id}/off-hire-periods")

    assert response.status_code == 200
    assert len(response.json()) == 1
