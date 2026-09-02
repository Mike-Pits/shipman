from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _set_rate(client, rate_date, usd_rub_rate):
    response = client.put(f"/exchange-rates/{rate_date}", json={"usd_rub_rate": usd_rub_rate})
    assert response.status_code == 200
    return response.json()


def test_a_rub_payment_needs_no_conversion(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "expense",
            "cost_type_name": "Port Charges",
            "original_currency": "RUB",
            "original_amount": 1234567.89,
            "invoice_date": "2026-06-01",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["rub_equivalent"] == 1234567.89
    assert created["exchange_rate_used"] is None
    assert created["status"] == "draft"


def test_a_usd_payment_is_converted_using_the_historical_rate_for_its_invoice_date(client):
    vessel_id = _create_vessel(client)
    _set_rate(client, "2026-06-01", 80.0)

    response = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "income",
            "cost_type_name": "Freight",
            "original_currency": "USD",
            "original_amount": 12500,
            "invoice_date": "2026-06-01",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["rub_equivalent"] == 1000000.0
    assert created["exchange_rate_used"] == 80.0
    assert created["exchange_rate_date"] == "2026-06-01"


def test_a_usd_payment_with_no_stored_rate_for_its_date_is_rejected(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "income",
            "cost_type_name": "Freight",
            "original_currency": "USD",
            "original_amount": 12500,
            "invoice_date": "2026-07-15",
        },
    )

    assert response.status_code == 422
    assert "exchange rate" in response.json()["detail"].lower()


def test_display_currency_toggle_converts_a_rub_payment_to_usd(client):
    vessel_id = _create_vessel(client)
    _set_rate(client, "2026-06-01", 80.0)
    created = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "expense",
            "cost_type_name": "Port Charges",
            "original_currency": "RUB",
            "original_amount": 800000,
            "invoice_date": "2026-06-01",
        },
    ).json()

    response = client.get(f"/payments/{created['id']}?display_currency=USD")

    assert response.status_code == 200
    body = response.json()
    assert body["original_amount"] == 800000
    assert body["original_currency"] == "RUB"
    assert body["display_currency"] == "USD"
    assert body["display_amount"] == 10000.0


def test_operator_can_progress_a_payment_through_its_status_workflow(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "expense",
            "cost_type_name": "Bunkers",
            "original_currency": "RUB",
            "original_amount": 50000,
            "invoice_date": "2026-06-01",
        },
    ).json()
    assert created["status"] == "draft"

    response = client.post(f"/payments/{created['id']}/status", json={"status": "paid"})

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_operator_can_list_and_retrieve_payments(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "cost_category": "expense",
            "cost_type_name": "Bunkers",
            "original_currency": "RUB",
            "original_amount": 50000,
            "invoice_date": "2026-06-01",
        },
    ).json()

    list_response = client.get("/payments")
    assert list_response.status_code == 200
    assert any(p["id"] == created["id"] for p in list_response.json())

    get_response = client.get(f"/payments/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["cost_type_name"] == "Bunkers"
