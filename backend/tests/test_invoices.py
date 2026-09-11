from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _set_rate(client, rate_date, usd_rub_rate):
    response = client.put(f"/exchange-rates/{rate_date}", json={"usd_rub_rate": usd_rub_rate})
    assert response.status_code == 200


def _create_fixture(client, **overrides):
    payload = {
        "fixture_type": "time_charter_out",
        "charterer": "Northern Charterers Ltd",
        "contract_currency": "RUB",
        "hire_rate": 9000.0,
        "hire_rate_basis": "daily",
        "charter_period_from": "2026-06-01",
        "charter_period_to": "2026-08-30",
        "hire_payment_basis": "advance",
        "hire_payment_frequency_days": 30,
        "brokers": [],
    }
    payload.update(overrides)
    return client.post("/fixtures", json=payload).json()["id"]


def _create_voyage_charter_fixture(client, **overrides):
    payload = {
        "fixture_type": "voyage_charter",
        "charterer": "Baltic Refineries Ltd",
        "contract_currency": "USD",
        "freight_rate": 25.0,
        "freight_rate_basis": "per_tonne",
        "load_port": "Primorsk",
        "discharge_port": "Rotterdam",
        "cargo_grade": "Diesel",
        "demurrage_rate": 12000.0,
        "brokers": [],
    }
    payload.update(overrides)
    return client.post("/fixtures", json=payload).json()["id"]


def _create_voyage(client, fixture_id, vessel_id, **overrides):
    payload = {
        "fixture_id": fixture_id,
        "vessel_id": vessel_id,
        "voyage_number": "V-001",
        "load_port": "Primorsk",
        "discharge_port": "Rotterdam",
        "start_date": "2026-06-01",
        "cargo_grade": "Diesel",
        "cargo_quantity_mt": 20000.0,
        "laden": True,
    }
    payload.update(overrides)
    return client.post("/voyages", json=payload).json()["id"]


# ---------------------------------------------------------------------------
# Hire invoices
# ---------------------------------------------------------------------------


def test_hire_invoice_computes_a_hire_line_and_issuing_creates_a_payment(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)

    create_response = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-07-01",
            "due_date": "2026-07-05",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    )
    assert create_response.status_code == 201
    draft = create_response.json()
    assert draft["status"] == "draft"
    assert draft["invoice_number"] is None
    assert len(draft["lines"]) == 1
    assert draft["lines"][0] == {
        "id": draft["lines"][0]["id"],
        "description": "Hire",
        "quantity": 10.0,
        "unit": "day",
        "unit_price": 9000.0,
        "amount": 90000.0,
    }
    assert draft["total_amount_due"] == 90000.0
    assert draft["currency"] == "RUB"

    issue_response = client.post(f"/invoices/{draft['id']}/issue")
    assert issue_response.status_code == 200
    issued = issue_response.json()
    assert issued["status"] == "issued"
    assert issued["invoice_number"] == "INV-2026-0001"
    assert issued["payment_id"] is not None

    payment = client.get(f"/payments/{issued['payment_id']}").json()
    assert payment["cost_type_name"] == "Hire"
    assert payment["cost_category"] == "income"
    assert payment["original_amount"] == 90000.0
    assert payment["status"] == "invoiced"
    assert payment["invoice_date"] == "2026-07-01"
    assert payment["due_date"] == "2026-07-05"


def test_hire_invoice_period_prorates_a_partial_final_day(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-07-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01 08:00",
            "hire_period_end": "2026-06-01 20:00",
        },
    )

    assert response.status_code == 201
    # half a day at 9000/day = 4500
    assert response.json()["total_amount_due"] == 4500.0


def test_hire_invoice_deducts_brokerage_per_broker_and_vat_is_computed_on_gross(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(
        client,
        vat_applicable=True,
        vat_treatment="exclusive",
        vat_rate_percent=20,
        brokers=[
            {"broker_name": "Broker A", "commission_percentage": 2.5},
            {"broker_name": "Broker B", "commission_percentage": 1.0},
        ],
    )

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-07-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    )

    assert response.status_code == 201
    body = response.json()
    # gross = 90000; VAT on gross (20%) = 18000 — brokerage never shrinks the VAT base
    assert body["vat_amount"] == 18000.0
    lines_by_desc = {line["description"]: line for line in body["lines"]}
    assert lines_by_desc["Hire"]["amount"] == 90000.0
    assert lines_by_desc["Brokerage — Broker A"]["amount"] == -2250.0
    assert lines_by_desc["Brokerage — Broker B"]["amount"] == -900.0
    # 90000 + 18000 (VAT) - 2250 - 900
    assert body["total_amount_due"] == 104850.0


def test_hire_invoice_rejects_a_non_tc_out_fixture(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client)

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-07-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    )

    assert response.status_code == 422


def test_hire_invoice_requires_fixture_vessel_and_period(client):
    response = client.post(
        "/invoices",
        json={"invoice_type": "hire", "date_of_issue": "2026-07-01"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Freight invoices
# ---------------------------------------------------------------------------


def test_freight_invoice_per_tonne_computes_from_voyage_and_fixture(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client)
    voyage_id = _create_voyage(client, fixture_id, vessel_id, cargo_quantity_mt=20000.0)

    response = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-01", "voyage_id": voyage_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["lines"][0] == {
        "id": body["lines"][0]["id"],
        "description": "Freight",
        "quantity": 20000.0,
        "unit": "MT",
        "unit_price": 25.0,
        "amount": 500000.0,
    }
    assert body["total_amount_due"] == 500000.0
    assert body["currency"] == "USD"
    assert body["counterparty"] == "Baltic Refineries Ltd"
    assert body["vessel_id"] == vessel_id


def test_freight_invoice_lump_sum_ignores_cargo_quantity(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(
        client, freight_rate=750000.0, freight_rate_basis="lump_sum"
    )
    voyage_id = _create_voyage(client, fixture_id, vessel_id)

    response = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-01", "voyage_id": voyage_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["lines"][0]["quantity"] == 1.0
    assert body["lines"][0]["unit"] == "lump sum"
    assert body["total_amount_due"] == 750000.0


def test_freight_invoice_covers_a_coa_lift_using_rate_per_tonne(client):
    vessel_id = _create_vessel(client)
    coa_fixture = client.post(
        "/fixtures",
        json={
            "fixture_type": "coa",
            "charterer": "Arctic Fuels Trading",
            "contract_currency": "USD",
            "contract_period_from": "2026-01-01",
            "contract_period_to": "2026-12-31",
            "rate_per_tonne": 22.0,
            "brokers": [],
        },
    ).json()
    voyage_id = _create_voyage(client, coa_fixture["id"], vessel_id, cargo_quantity_mt=12000.0)

    response = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-01", "voyage_id": voyage_id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["lines"][0]["unit_price"] == 22.0
    assert body["total_amount_due"] == 264000.0


def test_freight_invoice_with_brokers_deducts_each_as_its_own_line(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(
        client, brokers=[{"broker_name": "Sole Broker", "commission_percentage": 5.0}]
    )
    voyage_id = _create_voyage(client, fixture_id, vessel_id, cargo_quantity_mt=10000.0)

    response = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-01", "voyage_id": voyage_id},
    )

    assert response.status_code == 201
    body = response.json()
    # freight = 250000, brokerage 5% = 12500
    assert body["total_amount_due"] == 237500.0


# ---------------------------------------------------------------------------
# Demurrage invoices
# ---------------------------------------------------------------------------


def test_demurrage_invoice_takes_manually_entered_lines(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client, demurrage_rate=12000.0)
    voyage_id = _create_voyage(client, fixture_id, vessel_id)

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "demurrage",
            "date_of_issue": "2026-06-15",
            "voyage_id": voyage_id,
            "lines": [{"description": "Demurrage — Primorsk", "quantity": 1.5, "unit": "day", "unit_price": 12000.0}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total_amount_due"] == 18000.0
    # brokerage is never deducted from demurrage
    assert len(body["lines"]) == 1


def test_demurrage_invoice_linked_to_a_claim_auto_settles_it_on_issue(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client)
    voyage_id = _create_voyage(client, fixture_id, vessel_id)
    _set_rate(client, "2026-06-17", 80.0)
    claim = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "demurrage_dispute",
            "counterparty": "Baltic Refineries Ltd",
            "amount_claimed": 18000.0,
            "currency": "USD",
            "date_raised": "2026-06-16",
        },
    ).json()

    create_response = client.post(
        "/invoices",
        json={
            "invoice_type": "demurrage",
            "date_of_issue": "2026-06-17",
            "voyage_id": voyage_id,
            "claim_id": claim["id"],
            "lines": [{"description": "Demurrage", "quantity": 1.5, "unit": "day", "unit_price": 12000.0}],
        },
    )
    invoice = create_response.json()

    issue_response = client.post(f"/invoices/{invoice['id']}/issue")
    assert issue_response.status_code == 200

    settled_claim = client.get(f"/claims/{claim['id']}").json()
    assert settled_claim["status"] == "settled"
    assert settled_claim["amount_settled"] == 18000.0
    assert settled_claim["settled_payment_id"] == issue_response.json()["payment_id"]


def test_demurrage_invoice_requires_at_least_one_line(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client)
    voyage_id = _create_voyage(client, fixture_id, vessel_id)

    response = client.post(
        "/invoices",
        json={"invoice_type": "demurrage", "date_of_issue": "2026-06-15", "voyage_id": voyage_id, "lines": []},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Free-form invoices
# ---------------------------------------------------------------------------


def test_free_form_invoice_uses_operator_typed_lines_and_own_vat_terms(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "free_form",
            "date_of_issue": "2026-06-01",
            "vessel_id": vessel_id,
            "subject": "Agency reimbursement",
            "counterparty": "Baltic Agency LLC",
            "currency": "RUB",
            "vat_applicable": True,
            "vat_treatment": "exclusive",
            "vat_rate_percent": 20,
            "lines": [
                {"description": "Port dues reimbursement", "quantity": 1, "unit": "lump sum", "unit_price": 50000.0}
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total_amount_due"] == 60000.0
    assert body["subject"] == "Agency reimbursement"

    issue_response = client.post(f"/invoices/{body['id']}/issue")
    payment = client.get(f"/payments/{issue_response.json()['payment_id']}").json()
    assert payment["cost_type_name"] == "Agency reimbursement"


def test_free_form_invoice_requires_subject_counterparty_and_currency(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/invoices",
        json={
            "invoice_type": "free_form",
            "date_of_issue": "2026-06-01",
            "vessel_id": vessel_id,
            "lines": [{"description": "Misc", "quantity": 1, "unit": "ea", "unit_price": 100.0}],
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Numbering and lifecycle
# ---------------------------------------------------------------------------


def test_invoice_numbers_are_sequential_and_shared_across_types_and_never_reused(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    vc_fixture_id = _create_voyage_charter_fixture(client)
    voyage_id = _create_voyage(client, vc_fixture_id, vessel_id)
    _set_rate(client, "2026-06-02", 80.0)

    hire = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    ).json()
    freight = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-02", "voyage_id": voyage_id},
    ).json()

    hire_issued = client.post(f"/invoices/{hire['id']}/issue").json()
    assert hire_issued["invoice_number"] == "INV-2026-0001"
    freight_issued = client.post(f"/invoices/{freight['id']}/issue").json()
    assert freight_issued["invoice_number"] == "INV-2026-0002"

    client.post(f"/invoices/{hire_issued['id']}/void")
    third = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-03",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-07-01",
            "hire_period_end": "2026-07-05",
        },
    ).json()
    third_issued = client.post(f"/invoices/{third['id']}/issue").json()
    # INV-2026-0001 was voided but stays retired — never reused
    assert third_issued["invoice_number"] == "INV-2026-0003"


def test_an_issued_invoice_cannot_be_edited_or_deleted(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    draft = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    ).json()
    issued = client.post(f"/invoices/{draft['id']}/issue").json()

    edit_response = client.put(
        f"/invoices/{issued['id']}",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-20",
        },
    )
    assert edit_response.status_code == 409

    delete_response = client.delete(f"/invoices/{issued['id']}")
    assert delete_response.status_code == 409


def test_voiding_an_invoice_deletes_its_payment_and_retires_the_number(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    draft = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    ).json()
    issued = client.post(f"/invoices/{draft['id']}/issue").json()
    payment_id = issued["payment_id"]

    void_response = client.post(f"/invoices/{issued['id']}/void")
    assert void_response.status_code == 200
    voided = void_response.json()
    assert voided["status"] == "void"
    assert voided["invoice_number"] == "INV-2026-0001"
    assert voided["payment_id"] is None

    assert client.get(f"/payments/{payment_id}").status_code == 404


def test_voiding_a_claim_linked_demurrage_invoice_unsettles_the_claim(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client)
    voyage_id = _create_voyage(client, fixture_id, vessel_id)
    _set_rate(client, "2026-06-17", 80.0)
    claim = client.post(
        "/claims",
        json={
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "claim_type": "demurrage_dispute",
            "counterparty": "Baltic Refineries Ltd",
            "amount_claimed": 18000.0,
            "currency": "USD",
            "date_raised": "2026-06-16",
        },
    ).json()
    draft = client.post(
        "/invoices",
        json={
            "invoice_type": "demurrage",
            "date_of_issue": "2026-06-17",
            "voyage_id": voyage_id,
            "claim_id": claim["id"],
            "lines": [{"description": "Demurrage", "quantity": 1.5, "unit": "day", "unit_price": 12000.0}],
        },
    ).json()
    issued = client.post(f"/invoices/{draft['id']}/issue").json()

    client.post(f"/invoices/{issued['id']}/void")

    unsettled_claim = client.get(f"/claims/{claim['id']}").json()
    assert unsettled_claim["status"] == "negotiating"
    assert unsettled_claim["settled_payment_id"] is None
    assert unsettled_claim["amount_settled"] is None


def test_cannot_delete_a_payment_that_settles_an_issued_invoice(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    draft = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    ).json()
    issued = client.post(f"/invoices/{draft['id']}/issue").json()

    response = client.delete(f"/payments/{issued['payment_id']}")

    assert response.status_code == 409
    assert "void" in response.json()["detail"].lower()


def test_a_draft_invoice_can_be_freely_edited_and_deleted(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    draft = client.post(
        "/invoices",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-11",
        },
    ).json()

    edit_response = client.put(
        f"/invoices/{draft['id']}",
        json={
            "invoice_type": "hire",
            "date_of_issue": "2026-06-01",
            "fixture_id": fixture_id,
            "vessel_id": vessel_id,
            "hire_period_start": "2026-06-01",
            "hire_period_end": "2026-06-21",
        },
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["total_amount_due"] == 180000.0

    assert client.delete(f"/invoices/{draft['id']}").status_code == 204
    assert client.get(f"/invoices/{draft['id']}").status_code == 404


# ---------------------------------------------------------------------------
# P&L variance
# ---------------------------------------------------------------------------


def test_voyage_pnl_reports_variance_between_invoiced_and_collected(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_voyage_charter_fixture(client, contract_currency="RUB", freight_rate=25.0)
    voyage_id = _create_voyage(client, fixture_id, vessel_id, cargo_quantity_mt=20000.0)

    draft = client.post(
        "/invoices",
        json={"invoice_type": "freight", "date_of_issue": "2026-06-01", "voyage_id": voyage_id},
    ).json()
    issued = client.post(f"/invoices/{draft['id']}/issue").json()
    assert issued["total_amount_due_rub"] == 500000.0

    # charterer only paid 480000 — operator corrects the payment to match reality
    client.put(
        f"/payments/{issued['payment_id']}",
        json={
            "vessel_id": vessel_id,
            "voyage_id": voyage_id,
            "fixture_id": fixture_id,
            "cost_category": "income",
            "cost_type_name": "Freight",
            "original_currency": "RUB",
            "original_amount": 480000.0,
            "invoice_date": "2026-06-01",
            "status": "partial",
        },
    )

    pnl = client.get(f"/reports/voyage-pnl/{voyage_id}").json()
    assert pnl["revenue"] == 480000.0
    assert pnl["invoiced_revenue"] == 500000.0
    assert pnl["variance_vs_invoiced"] == -20000.0
