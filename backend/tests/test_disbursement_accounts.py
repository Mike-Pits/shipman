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
    voyage = client.post(
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
    ).json()
    return voyage["id"]


def test_operator_can_record_a_pda_for_a_port_call(client):
    voyage_id = _create_voyage(client)

    response = client.post(
        "/disbursement-accounts",
        json={
            "voyage_id": voyage_id,
            "port": "Rotterdam",
            "pda_amount": 15000,
            "pda_currency": "USD",
            "pda_date": "2026-06-05",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "pda_only"
    assert created["fda_total"] == 0
    assert created["variance"] == -15000


def test_pda_rejects_a_currency_other_than_rub_or_usd(client):
    voyage_id = _create_voyage(client)

    response = client.post(
        "/disbursement-accounts",
        json={
            "voyage_id": voyage_id,
            "port": "Rotterdam",
            "pda_amount": 15000,
            "pda_currency": "EUR",
            "pda_date": "2026-06-05",
        },
    )

    assert response.status_code == 422


def test_adding_fda_lines_computes_total_and_variance_and_moves_to_fda_pending(client):
    voyage_id = _create_voyage(client)
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

    response = client.post(
        f"/disbursement-accounts/{da['id']}/fda-lines",
        json={
            "lines": [
                {"line_type": "pilotage", "description": "Inbound pilot", "amount": 3000, "currency": "USD"},
                {"line_type": "agency_fee", "description": "Agency fee", "amount": 13500, "currency": "USD"},
            ]
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "fda_pending"
    assert updated["fda_total"] == 16500
    assert updated["variance"] == 1500


def test_operator_can_reconcile_a_da_with_fda_lines(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()
    client.post(
        f"/disbursement-accounts/{da['id']}/fda-lines",
        json={"lines": [{"line_type": "pilotage", "description": "Inbound pilot", "amount": 3000, "currency": "USD"}]},
    )

    response = client.post(f"/disbursement-accounts/{da['id']}/reconcile")

    assert response.status_code == 200
    assert response.json()["status"] == "reconciled"


def test_reconciling_a_da_with_no_fda_lines_is_rejected(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    response = client.post(f"/disbursement-accounts/{da['id']}/reconcile")

    assert response.status_code == 409


def test_operator_can_mark_a_da_as_disputed(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    response = client.post(f"/disbursement-accounts/{da['id']}/dispute")

    assert response.status_code == 200
    assert response.json()["status"] == "disputed"


def test_operator_can_list_and_retrieve_disbursement_accounts(client):
    voyage_id = _create_voyage(client)
    created = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    list_response = client.get("/disbursement-accounts")
    assert list_response.status_code == 200
    assert any(d["id"] == created["id"] for d in list_response.json())

    get_response = client.get(f"/disbursement-accounts/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["port"] == "Rotterdam"


def test_operator_can_correct_the_pda_header_fields(client):
    voyage_id = _create_voyage(client)
    created = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    response = client.put(
        f"/disbursement-accounts/{created['id']}",
        json={"voyage_id": voyage_id, "port": "Rotterdam Port", "pda_amount": 16000, "pda_currency": "USD", "pda_date": "2026-06-06"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["port"] == "Rotterdam Port"
    assert updated["pda_amount"] == 16000
    assert updated["variance"] == -16000


def test_correcting_a_da_for_an_unknown_voyage_is_rejected(client):
    voyage_id = _create_voyage(client)
    created = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    response = client.put(
        f"/disbursement-accounts/{created['id']}",
        json={"voyage_id": 999999, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    )

    assert response.status_code == 404


def test_correcting_the_pda_header_preserves_status_and_fda_lines(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()
    client.post(
        f"/disbursement-accounts/{da['id']}/fda-lines",
        json={"lines": [{"line_type": "pilotage", "description": "Inbound pilot", "amount": 3000, "currency": "USD"}]},
    )

    response = client.put(
        f"/disbursement-accounts/{da['id']}",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 16000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "fda_pending"
    assert len(updated["lines"]) == 1


def test_operator_can_correct_an_individual_fda_line(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()
    with_line = client.post(
        f"/disbursement-accounts/{da['id']}/fda-lines",
        json={"lines": [{"line_type": "pilotage", "description": "Inbound pilot", "amount": 3000, "currency": "USD"}]},
    ).json()
    line_id = with_line["lines"][0]["id"]

    response = client.put(
        f"/disbursement-accounts/{da['id']}/fda-lines/{line_id}",
        json={"line_type": "pilotage", "description": "Inbound pilot (corrected)", "amount": 3200, "currency": "USD"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["lines"][0]["description"] == "Inbound pilot (corrected)"
    assert updated["lines"][0]["amount"] == 3200
    assert updated["fda_total"] == 3200
    assert updated["variance"] == -11800


def test_correcting_an_fda_line_that_does_not_belong_to_the_da_is_rejected(client):
    voyage_id = _create_voyage(client)
    da = client.post(
        "/disbursement-accounts",
        json={"voyage_id": voyage_id, "port": "Rotterdam", "pda_amount": 15000, "pda_currency": "USD", "pda_date": "2026-06-05"},
    ).json()

    response = client.put(
        f"/disbursement-accounts/{da['id']}/fda-lines/999999",
        json={"line_type": "pilotage", "description": "Inbound pilot", "amount": 3000, "currency": "USD"},
    )

    assert response.status_code == 404
