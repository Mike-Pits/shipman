from datetime import date, timedelta

from tests.test_vessels import vessel_payload


_next_imo = iter(range(9100000, 9199999))


def _create_voyage_with_payment(client, income_amount, invoice_date="2026-06-01"):
    vessel_id = client.post(
        "/vessels", json=vessel_payload(imo_number=str(next(_next_imo)))
    ).json()["id"]
    fixture_id = client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "RUB",
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
    client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "voyage_id": voyage_id,
            "cost_category": "income",
            "cost_type_name": "Freight",
            "original_currency": "RUB",
            "original_amount": income_amount,
            "invoice_date": invoice_date,
        },
    )
    return voyage_id, vessel_id


def test_fleet_pnl_aggregates_across_voyages_within_the_period(client):
    _create_voyage_with_payment(client, 500000, invoice_date="2026-06-05")
    _create_voyage_with_payment(client, 300000, invoice_date="2026-06-20")
    _create_voyage_with_payment(client, 999999, invoice_date="2026-07-15")  # outside period

    response = client.get(
        "/reports/fleet-pnl?start_date=2026-06-01&end_date=2026-06-30"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["revenue"] == 800000
    assert body["voyage_count"] == 2


def test_da_reconciliation_report_flags_unreconciled_and_disputed(client):
    _, vessel_id = _create_voyage_with_payment(client, 100000)
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
            "voyage_number": "V-002",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "start_date": "2026-06-01",
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    ).json()["id"]
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()  # left as pda_only -> unreconciled

    response = client.get("/reports/da-reconciliation")

    assert response.status_code == 200
    flagged_ids = {row["id"] for row in response.json()}
    assert da["id"] in flagged_ids


def test_fleet_vetting_status_report_lists_every_vessel(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]

    response = client.get("/reports/vetting-status")

    assert response.status_code == 200
    ids = {row["vessel_id"] for row in response.json()}
    assert vessel_id in ids


def test_claims_status_report_shows_age_in_days(client):
    voyage_id, _ = _create_voyage_with_payment(client, 100000)
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 15000,
            "currency": "USD",
            "date_raised": ten_days_ago,
        },
    )

    response = client.get("/reports/claims-status")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["age_days"] == 10
