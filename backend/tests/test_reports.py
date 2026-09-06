from tests.test_vessels import vessel_payload


_next_imo = iter(range(9000000, 9999999))


def _create_voyage(client, start_date="2026-06-01", end_date=None):
    imo_number = str(next(_next_imo))
    vessel_id = client.post("/vessels", json=vessel_payload(imo_number=imo_number)).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "RUB",
            "freight_rate": 25.0,
            "freight_rate_basis": "per_tonne",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "cargo_grade": "gasoil",
        },
    ).json()["id"]
    voyage = client.post(
        "/voyages",
        json={
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "voyage_number": "V-001",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "start_date": start_date,
            "end_date": end_date,
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    ).json()
    return voyage["id"], vessel_id


def _create_payment(client, vessel_id, voyage_id, cost_category, cost_type_name, amount):
    return client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "voyage_id": voyage_id,
            "cost_category": cost_category,
            "cost_type_name": cost_type_name,
            "original_currency": "RUB",
            "original_amount": amount,
            "invoice_date": "2026-06-01",
        },
    ).json()


def test_voyage_pnl_sums_income_and_expense_payments_linked_to_the_voyage(client):
    voyage_id, vessel_id = _create_voyage(client)
    _create_payment(client, vessel_id, voyage_id, "income", "Freight", 500000)
    _create_payment(client, vessel_id, voyage_id, "expense", "Bunkers", 120000)

    response = client.get(f"/reports/voyage-pnl/{voyage_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["revenue"] == 500000
    assert body["costs"] == 120000
    assert body["net_result"] == 380000


def test_voyage_pnl_reconciles_against_its_originating_estimate(client):
    estimate = client.post(
        "/voyage-estimates",
        json={
            "vessel_id": None,
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "laycan_start": "2026-06-01",
            "laycan_end": "2026-06-05",
            "cargo_grade": "gasoil",
            "estimated_cargo_quantity_mt": 5000,
            "estimated_rate": 30,
            "estimated_rate_basis": "per_tonne",
            "currency": "RUB",
            "estimated_bunker_consumption_mt": 200,
            "estimated_bunker_cost": 90000,
            "estimated_port_costs": 10000,
            "estimated_duration_days": 10,
        },
    ).json()
    # estimated_net_result = (30*5000) - (90000+10000) = 150000 - 100000 = 50000
    fixture = client.post(
        f"/voyage-estimates/{estimate['id']}/promote",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "RUB",
            "freight_rate": 30,
            "freight_rate_basis": "per_tonne",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "cargo_grade": "gasoil",
        },
    ).json()
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    voyage_id = client.post(
        "/voyages",
        json={
            "fixture_id": fixture["id"],
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
    _create_payment(client, vessel_id, voyage_id, "income", "Freight", 150000)
    _create_payment(client, vessel_id, voyage_id, "expense", "Bunkers", 110000)
    # actual net_result = 150000 - 110000 = 40000; variance vs. 50000 estimate = -10000

    response = client.get(f"/reports/voyage-pnl/{voyage_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["estimated_net_result"] == 50000
    assert body["variance_vs_estimate"] == -10000


def test_voyage_pnl_omits_estimate_fields_when_there_is_no_originating_estimate(client):
    voyage_id, vessel_id = _create_voyage(client)
    _create_payment(client, vessel_id, voyage_id, "income", "Freight", 500000)

    response = client.get(f"/reports/voyage-pnl/{voyage_id}")

    assert "estimated_net_result" not in response.json()


def test_voyage_pnl_excludes_payments_linked_to_other_voyages(client):
    voyage_id, vessel_id = _create_voyage(client)
    other_voyage_id, _ = _create_voyage(client)
    _create_payment(client, vessel_id, voyage_id, "income", "Freight", 500000)
    _create_payment(client, vessel_id, other_voyage_id, "income", "Freight", 999999)

    response = client.get(f"/reports/voyage-pnl/{voyage_id}")

    assert response.json()["revenue"] == 500000


def test_tce_divides_net_result_by_voyage_duration_in_days(client):
    voyage_id, vessel_id = _create_voyage(client, start_date="2026-06-01", end_date="2026-06-11")
    _create_payment(client, vessel_id, voyage_id, "income", "Freight", 500000)
    _create_payment(client, vessel_id, voyage_id, "expense", "Bunkers", 120000)

    response = client.get(f"/reports/tce/{voyage_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["duration_days"] == 10
    assert body["tce_per_day"] == 38000


def test_tce_excludes_off_hire_days_from_the_duration_denominator(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "time_charter_out",
            "charterer": "Northern Charterers Ltd",
            "contract_currency": "RUB",
            "hire_rate": 9000,
            "hire_rate_basis": "daily",
            "charter_period_from": "2026-06-01",
            "charter_period_to": "2026-06-11",
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
            "end_date": "2026-06-11",
            "cargo_grade": "n/a",
            "cargo_quantity_mt": 0,
            "laden": False,
        },
    ).json()["id"]
    _create_payment(client, vessel_id, voyage_id, "income", "Hire", 90000)
    client.post(
        f"/voyages/{voyage_id}/off-hire-periods",
        json={
            "start_datetime": "2026-06-05 00:00:00",
            "end_datetime": "2026-06-07 00:00:00",
            "reason": "Main engine breakdown",
        },
    )

    response = client.get(f"/reports/tce/{voyage_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["duration_days"] == 10
    assert body["off_hire_days"] == 2
    assert body["earning_days"] == 8
    assert body["tce_per_day"] == 11250


def test_tce_requires_the_voyage_to_have_an_end_date(client):
    voyage_id, vessel_id = _create_voyage(client, start_date="2026-06-01", end_date=None)

    response = client.get(f"/reports/tce/{voyage_id}")

    assert response.status_code == 422


def test_tce_treats_an_empty_string_end_date_as_unset_rather_than_erroring(client):
    voyage_id, vessel_id = _create_voyage(client, start_date="2026-06-01", end_date="")

    response = client.get(f"/reports/tce/{voyage_id}")

    assert response.status_code == 422
