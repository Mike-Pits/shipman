import json

from tests.test_vessels import vessel_payload


def test_creating_a_vessel_is_not_audit_logged(client):
    client.post("/vessels", json=vessel_payload())

    log = client.get("/audit-log?table_name=vessels").json()

    assert log == []


def test_creating_a_fixture_produces_an_insert_audit_entry(client):
    fixture = client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 25.0,
            "freight_rate_basis": "per_tonne",
        },
    ).json()

    log = client.get("/audit-log?table_name=fixtures").json()

    assert len(log) == 1
    assert log[0]["action"] == "insert"
    assert log[0]["record_id"] == fixture["id"]
    new_values = json.loads(log[0]["new_values"])
    assert new_values["charterer"] == "Test Charterer"


def test_updating_a_payment_produces_an_update_entry_with_old_and_new_values(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    payment = client.post(
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

    client.get(f"/payments/{payment['id']}")  # sanity: read doesn't itself create an entry
    client.post(f"/payments/{payment['id']}/status", json={"status": "paid"})

    log = client.get("/audit-log?table_name=payments").json()

    assert len(log) == 2
    assert log[0]["action"] == "insert"
    assert log[1]["action"] == "update"
    old_values = json.loads(log[1]["old_values"])
    new_values = json.loads(log[1]["new_values"])
    assert old_values["status"] == "draft"
    assert new_values["status"] == "paid"


def test_a_manual_exchange_rate_override_is_audit_logged_but_a_plain_fetch_is_not(client):
    client.put("/exchange-rates/2026-06-01", json={"usd_rub_rate": 80.0})

    log = client.get("/audit-log?table_name=exchange_rates").json()

    assert len(log) == 1
    assert log[0]["action"] == "insert"
    new_values = json.loads(log[0]["new_values"])
    assert new_values["usd_rub_rate"] == 80.0


def test_overriding_an_existing_rate_produces_an_update_entry_with_the_old_rate(client):
    client.put("/exchange-rates/2026-06-01", json={"usd_rub_rate": 80.0})
    client.put("/exchange-rates/2026-06-01", json={"usd_rub_rate": 82.5})

    log = client.get("/audit-log?table_name=exchange_rates").json()

    assert len(log) == 2
    assert log[1]["action"] == "update"
    old_values = json.loads(log[1]["old_values"])
    new_values = json.loads(log[1]["new_values"])
    assert old_values["usd_rub_rate"] == 80.0
    assert new_values["usd_rub_rate"] == 82.5
