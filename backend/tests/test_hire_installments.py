from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _create_tc_out_fixture(client, **overrides):
    payload = {
        "fixture_type": "time_charter_out",
        "charterer": "Northern Charterers Ltd",
        "contract_currency": "RUB",
        "hire_rate": 9000,
        "hire_rate_basis": "daily",
        "charter_period_from": "2026-06-01",
        "charter_period_to": "2026-08-30",
        "delivery_port": "Ust-Luga",
        "hire_payment_basis": "advance",
        "hire_payment_frequency_days": 30,
    }
    payload.update(overrides)
    return client.post("/fixtures", json=payload).json()["id"]


def test_advance_basis_generates_installments_invoiced_and_due_at_period_start(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_tc_out_fixture(client)

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 201
    installments = response.json()
    assert len(installments) == 3
    first = installments[0]
    assert first["invoice_date"] == "2026-06-01"
    assert first["due_date"] == "2026-06-01"
    assert first["original_amount"] == 270000
    assert first["cost_category"] == "income"
    assert first["cost_type_name"] == "Hire"
    assert first["vessel_id"] == vessel_id
    assert first["fixture_id"] == fixture_id


def test_arrears_basis_generates_installments_invoiced_and_due_at_period_end(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_tc_out_fixture(client, hire_payment_basis="arrears")

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 201
    first = response.json()[0]
    assert first["invoice_date"] == "2026-07-01"
    assert first["due_date"] == "2026-07-01"


def test_days_after_invoice_basis_offsets_the_due_date(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_tc_out_fixture(
        client, hire_payment_basis="days_after_invoice", hire_payment_days_after_invoice=15
    )

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 201
    first = response.json()[0]
    assert first["invoice_date"] == "2026-06-01"
    assert first["due_date"] == "2026-06-16"


def test_generating_installments_for_a_non_tc_out_fixture_is_rejected(client):
    vessel_id = _create_vessel(client)
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

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 422
