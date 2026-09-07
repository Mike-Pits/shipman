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


def test_days_after_invoice_basis_can_be_anchored_to_the_real_invoice_date(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_tc_out_fixture(
        client, hire_payment_basis="days_after_invoice", hire_payment_days_after_invoice=15
    )

    # the owner actually issued the first invoice 3 days after the period technically
    # started — the whole installment schedule should shift by that same 3 days
    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments",
        json={"vessel_id": vessel_id, "invoice_date_override": "2026-06-04"},
    )

    assert response.status_code == 201
    installments = response.json()
    assert installments[0]["invoice_date"] == "2026-06-04"
    assert installments[0]["due_date"] == "2026-06-19"
    assert installments[1]["invoice_date"] == "2026-07-04"


def test_invoice_date_override_is_ignored_for_advance_basis(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_tc_out_fixture(client, hire_payment_basis="advance")

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments",
        json={"vessel_id": vessel_id, "invoice_date_override": "2026-06-04"},
    )

    assert response.status_code == 201
    # advance billing is contractually fixed to the period start regardless of the override
    assert response.json()[0]["invoice_date"] == "2026-06-01"


def test_final_installment_is_prorated_for_a_partial_day_at_redelivery(client):
    vessel_id = _create_vessel(client)
    # delivery 08:00, redelivery 20:00 — the second (final) installment covers 14 days
    # and 12 hours, not a whole number of days, and must be billed for exactly that
    fixture_id = _create_tc_out_fixture(
        client,
        charter_period_from="2026-06-01 08:00",
        charter_period_to="2026-07-15 20:00",
        hire_rate=10000,
    )

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 201
    installments = response.json()
    assert len(installments) == 2
    assert installments[0]["original_amount"] == 300000  # full 30-day chunk
    assert installments[1]["original_amount"] == 145000  # 14.5-day final chunk


def test_charter_period_accepts_a_bare_date_or_a_datetime_with_or_without_seconds(client):
    vessel_id = _create_vessel(client)

    # matches what an operator naturally typed for a real fixture: no seconds
    fixture_id = _create_tc_out_fixture(
        client,
        charter_period_from="2026-06-01 13:50",
        charter_period_to="2026-06-01 13:50",  # will be pushed out below
    )
    # zero-length period generates nothing; extend it slightly to get one installment
    client.put(
        f"/fixtures/{fixture_id}",
        json={
            "fixture_type": "time_charter_out",
            "charterer": "Northern Charterers Ltd",
            "contract_currency": "RUB",
            "hire_rate": 9000,
            "hire_rate_basis": "daily",
            "charter_period_from": "2026-06-01 13:50",
            "charter_period_to": "2026-06-02 13:50",
            "delivery_port": "Ust-Luga",
            "hire_payment_basis": "advance",
            "hire_payment_frequency_days": 30,
            "brokers": [],
        },
    )

    response = client.post(
        f"/fixtures/{fixture_id}/generate-hire-installments", json={"vessel_id": vessel_id}
    )

    assert response.status_code == 201
    assert response.json()[0]["original_amount"] == 9000  # exactly one full day


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
