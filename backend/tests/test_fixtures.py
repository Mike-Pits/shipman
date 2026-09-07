def voyage_charter_payload(**overrides):
    payload = {
        "fixture_type": "voyage_charter",
        "charterer": "Baltic Refineries Ltd",
        "contract_currency": "USD",
        "freight_rate": 25.50,
        "freight_rate_basis": "per_tonne",
        "laycan_start": "2026-09-01",
        "laycan_end": "2026-09-05",
        "load_port": "Primorsk",
        "discharge_port": "Rotterdam",
        "cargo_grade": "Diesel",
        "demurrage_rate": 12000.0,
        "despatch_rate": 6000.0,
        "laytime_terms": "72 hours SHINC",
        "brokers": [],
    }
    payload.update(overrides)
    return payload


def time_charter_out_payload(**overrides):
    payload = {
        "fixture_type": "time_charter_out",
        "charterer": "Nordic Tankers AS",
        "contract_currency": "USD",
        "hire_rate": 14500.0,
        "hire_rate_basis": "daily",
        "charter_period_from": "2026-10-01",
        "charter_period_to": "2027-01-01",
        "delivery_port": "St. Petersburg",
        "redelivery_port": "Gdansk",
        "redelivery_conditions": "Same condition as on delivery, tanks clean",
        "hire_payment_basis": "days_after_invoice",
        "hire_payment_frequency_days": 15,
        "hire_payment_days_after_invoice": 5,
        "brokers": [],
    }
    payload.update(overrides)
    return payload


def test_operator_can_create_a_time_charter_out_fixture_with_configured_payment_terms(client):
    create_response = client.post("/fixtures", json=time_charter_out_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["fixture_type"] == "time_charter_out"
    assert created["hire_rate"] == 14500.0
    assert created["hire_payment_basis"] == "days_after_invoice"
    assert created["hire_payment_days_after_invoice"] == 5

    # a different fixture can use a completely different payment basis —
    # terms are per-fixture, not a system-wide assumption (FR-08)
    advance_response = client.post(
        "/fixtures",
        json=time_charter_out_payload(
            charterer="Other Charterer",
            hire_payment_basis="advance",
            hire_payment_frequency_days=30,
            hire_payment_days_after_invoice=None,
        ),
    )
    assert advance_response.status_code == 201
    assert advance_response.json()["hire_payment_basis"] == "advance"


def test_time_charter_out_fixture_records_delivery_and_redelivery_rob(client):
    payload = time_charter_out_payload(
        delivery_rob_ifo_mt=450.5,
        delivery_rob_mgo_mt=30.0,
        redelivery_rob_ifo_mt=200.0,
        redelivery_rob_mgo_mt=15.25,
    )

    create_response = client.post("/fixtures", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["delivery_rob_ifo_mt"] == 450.5
    assert created["delivery_rob_mgo_mt"] == 30.0
    assert created["redelivery_rob_ifo_mt"] == 200.0
    assert created["redelivery_rob_mgo_mt"] == 15.25

    fetched = client.get(f"/fixtures/{created['id']}").json()
    assert fetched["delivery_rob_ifo_mt"] == 450.5
    assert fetched["redelivery_rob_mgo_mt"] == 15.25


def coa_payload(**overrides):
    payload = {
        "fixture_type": "coa",
        "charterer": "Arctic Fuels Trading",
        "contract_currency": "USD",
        "contract_period_from": "2026-01-01",
        "contract_period_to": "2026-12-31",
        "cargo_grade": "Gasoil",
        "total_contracted_quantity": 120000.0,
        "number_of_lifts": 12,
        "rate_per_tonne": 22.0,
        "min_cargo_quantity_per_lift": 8000.0,
        "max_cargo_quantity_per_lift": 12000.0,
        "brokers": [],
    }
    payload.update(overrides)
    return payload


def test_operator_can_create_and_retrieve_a_coa_fixture(client):
    create_response = client.post("/fixtures", json=coa_payload())

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["fixture_type"] == "coa"
    assert created["number_of_lifts"] == 12
    assert created["total_contracted_quantity"] == 120000.0

    fetched = client.get(f"/fixtures/{created['id']}").json()
    assert fetched["min_cargo_quantity_per_lift"] == 8000.0
    assert fetched["max_cargo_quantity_per_lift"] == 12000.0


def test_fixture_supports_up_to_three_brokers_with_commissions(client):
    payload = voyage_charter_payload(
        brokers=[
            {"broker_name": "Broker A", "commission_percentage": 1.25},
            {"broker_name": "Broker B", "commission_percentage": 1.0},
            {"broker_name": "Broker C", "commission_percentage": 0.5},
        ]
    )

    create_response = client.post("/fixtures", json=payload)

    assert create_response.status_code == 201
    brokers = create_response.json()["brokers"]
    assert len(brokers) == 3
    assert {b["broker_name"] for b in brokers} == {"Broker A", "Broker B", "Broker C"}


def test_fixture_rejects_a_fourth_broker(client):
    payload = voyage_charter_payload(
        brokers=[
            {"broker_name": "Broker A", "commission_percentage": 1.0},
            {"broker_name": "Broker B", "commission_percentage": 1.0},
            {"broker_name": "Broker C", "commission_percentage": 1.0},
            {"broker_name": "Broker D", "commission_percentage": 1.0},
        ]
    )

    response = client.post("/fixtures", json=payload)

    assert response.status_code == 422


def test_fixture_records_date_concluded_and_charter_party_details(client):
    payload = voyage_charter_payload(
        date_concluded="2026-08-15",
        charter_party_ref="CP-2026-0042",
        charter_party_type="ASBATANKVOY",
    )

    create_response = client.post("/fixtures", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["date_concluded"] == "2026-08-15"
    assert created["charter_party_ref"] == "CP-2026-0042"
    assert created["charter_party_type"] == "ASBATANKVOY"

    fetched = client.get(f"/fixtures/{created['id']}").json()
    assert fetched["charter_party_ref"] == "CP-2026-0042"


def test_fixture_rejects_a_contract_currency_other_than_rub_or_usd(client):
    payload = voyage_charter_payload(contract_currency="EUR")

    response = client.post("/fixtures", json=payload)

    assert response.status_code == 422


def test_fixture_charter_party_ref_rejects_more_than_15_characters(client):
    payload = voyage_charter_payload(charter_party_ref="THIS-REF-IS-WAY-TOO-LONG")

    response = client.post("/fixtures", json=payload)

    assert response.status_code == 422


def test_operator_can_list_fixtures_of_different_types(client):
    client.post("/fixtures", json=voyage_charter_payload())
    client.post("/fixtures", json=time_charter_out_payload())
    client.post("/fixtures", json=coa_payload())

    list_response = client.get("/fixtures")

    assert list_response.status_code == 200
    fixture_types = {f["fixture_type"] for f in list_response.json()}
    assert fixture_types == {"voyage_charter", "time_charter_out", "coa"}


def test_operator_can_create_and_retrieve_a_voyage_charter_fixture(client):
    create_response = client.post("/fixtures", json=voyage_charter_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] is not None
    assert created["fixture_type"] == "voyage_charter"
    assert created["charterer"] == "Baltic Refineries Ltd"
    assert created["freight_rate"] == 25.50
    assert created["load_port"] == "Primorsk"

    get_response = client.get(f"/fixtures/{created['id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["fixture_type"] == "voyage_charter"
    assert fetched["discharge_port"] == "Rotterdam"


def test_operator_can_update_a_fixture(client):
    created = client.post("/fixtures", json=voyage_charter_payload()).json()

    response = client.put(
        f"/fixtures/{created['id']}",
        json=voyage_charter_payload(charterer="Corrected Charterer Name"),
    )

    assert response.status_code == 200
    assert response.json()["charterer"] == "Corrected Charterer Name"
    assert client.get(f"/fixtures/{created['id']}").json()["charterer"] == "Corrected Charterer Name"


def test_updating_a_fixture_replaces_its_brokers(client):
    created = client.post(
        "/fixtures",
        json=voyage_charter_payload(brokers=[{"broker_name": "Old Broker", "commission_percentage": 1.0}]),
    ).json()

    response = client.put(
        f"/fixtures/{created['id']}",
        json=voyage_charter_payload(brokers=[{"broker_name": "New Broker", "commission_percentage": 2.0}]),
    )

    assert response.status_code == 200
    brokers = response.json()["brokers"]
    assert len(brokers) == 1
    assert brokers[0]["broker_name"] == "New Broker"


def test_updating_an_unknown_fixture_returns_404(client):
    response = client.put("/fixtures/999", json=voyage_charter_payload())

    assert response.status_code == 404
