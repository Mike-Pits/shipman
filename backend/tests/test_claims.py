from tests.test_vessels import vessel_payload


def _create_voyage(client):
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
            "start_date": "2026-06-01",
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    ).json()["id"]
    return voyage_id, fixture_id, vessel_id


def test_operator_can_record_a_claim_linked_to_a_voyage(client):
    voyage_id, fixture_id, _ = _create_voyage(client)

    response = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 15000,
            "currency": "USD",
            "date_raised": "2026-06-15",
            "notes": "Shortlanded 50 MT per draft survey",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "open"
    assert created["amount_settled"] is None


def test_claim_rejects_a_currency_other_than_rub_or_usd(client):
    voyage_id, fixture_id, _ = _create_voyage(client)

    response = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 15000,
            "currency": "EUR",
            "date_raised": "2026-06-15",
        },
    )

    assert response.status_code == 422


def test_claims_are_excluded_from_voyage_pnl_while_open(client):
    voyage_id, fixture_id, vessel_id = _create_voyage(client)
    client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "voyage_id": voyage_id,
            "cost_category": "income",
            "cost_type_name": "Freight",
            "original_currency": "RUB",
            "original_amount": 500000,
            "invoice_date": "2026-06-01",
        },
    )
    client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 999999,
            "currency": "RUB",
            "date_raised": "2026-06-15",
        },
    )

    pnl = client.get(f"/reports/voyage-pnl/{voyage_id}").json()

    assert pnl["revenue"] == 500000


def test_operator_can_settle_a_claim_and_link_it_to_a_payment(client):
    voyage_id, fixture_id, vessel_id = _create_voyage(client)
    claim = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "demurrage_dispute",
            "counterparty": "Test Charterer",
            "amount_claimed": 20000,
            "currency": "USD",
            "date_raised": "2026-06-15",
        },
    ).json()
    payment = client.post(
        "/payments",
        json={
            "vessel_id": vessel_id,
            "voyage_id": voyage_id,
            "cost_category": "income",
            "cost_type_name": "Demurrage",
            "original_currency": "RUB",
            "original_amount": 17000,
            "invoice_date": "2026-07-01",
        },
    ).json()

    response = client.post(
        f"/claims/{claim['id']}/settle",
        json={"amount_settled": 17000, "payment_id": payment["id"]},
    )

    assert response.status_code == 200
    settled = response.json()
    assert settled["status"] == "settled"
    assert settled["amount_settled"] == 17000
    assert settled["settled_payment_id"] == payment["id"]
    assert settled["date_resolved"] is not None


def test_a_claim_can_be_linked_to_a_disputed_disbursement_account(client):
    voyage_id, fixture_id, _ = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={
            "voyage_id": voyage_id,
            "port": "Rotterdam",
            "pda_amount": 15000,
            "pda_currency": "USD",
            "pda_date": "2026-06-05",
        },
    ).json()
    client.post(f"/disbursement-accounts/{da['id']}/dispute")

    response = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "disbursement_account_id": da["id"],
            "claim_type": "other",
            "counterparty": "Rotterdam Port Agent",
            "amount_claimed": 3000,
            "currency": "USD",
            "date_raised": "2026-06-10",
        },
    )

    assert response.status_code == 201
    assert response.json()["disbursement_account_id"] == da["id"]


def test_operator_can_list_and_filter_claims_by_status(client):
    voyage_id, fixture_id, _ = _create_voyage(client)
    client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "other",
            "counterparty": "Test Charterer",
            "amount_claimed": 1000,
            "currency": "USD",
            "date_raised": "2026-06-15",
        },
    )

    response = client.get("/claims?status=open")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_operator_can_correct_a_claims_fields(client):
    voyage_id, fixture_id, _ = _create_voyage(client)
    created = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 15000,
            "currency": "USD",
            "date_raised": "2026-06-15",
            "notes": "Shortlanded 50 MT per draft survey",
        },
    ).json()

    response = client.put(
        f"/claims/{created['id']}",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 17500,
            "currency": "USD",
            "date_raised": "2026-06-16",
            "notes": "Corrected after re-survey: shortlanded 58 MT",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["amount_claimed"] == 17500
    assert updated["date_raised"] == "2026-06-16"
    assert updated["notes"] == "Corrected after re-survey: shortlanded 58 MT"


def test_correcting_a_claim_preserves_its_status_and_settlement_fields(client):
    voyage_id, fixture_id, _ = _create_voyage(client)
    created = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd",
            "amount_claimed": 15000,
            "currency": "USD",
            "date_raised": "2026-06-15",
        },
    ).json()
    client.post(f"/claims/{created['id']}/status", json={"status": "negotiating"})

    response = client.put(
        f"/claims/{created['id']}",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "cargo_quantity",
            "counterparty": "Rotterdam Terminal Ltd (corrected)",
            "amount_claimed": 15000,
            "currency": "USD",
            "date_raised": "2026-06-15",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "negotiating"
    assert updated["counterparty"] == "Rotterdam Terminal Ltd (corrected)"


def test_correcting_an_unknown_claim_returns_404(client):
    response = client.put(
        "/claims/999999",
        json={
            "claim_type": "other",
            "counterparty": "Test Charterer",
            "amount_claimed": 1000,
            "currency": "USD",
            "date_raised": "2026-06-15",
        },
    )

    assert response.status_code == 404
