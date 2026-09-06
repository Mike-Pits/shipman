from datetime import date, timedelta

from tests.test_vessels import vessel_payload

SAMPLE_DISP01 = """т/к СП Дудинка
Дисп. 05/04-2026
1 2705/0800
2 6457N/04000E
4 340/7
5 340/1
6 040/8,3
10 114
11 597
31 232,26/46,108
36 43
43 Архангельск
44 1812/0800
NNNN"""


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def test_operator_can_submit_a_disp01_report_and_it_is_parsed_and_saved(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01},
    )

    assert response.status_code == 201
    created = response.json()
    assert created["vessel_id"] == vessel_id
    assert created["report_datetime"] == "2026-05-27 08:00:00"
    assert created["fields"]["43"] == "Архангельск"
    assert created["fields"]["11"] == "597"
    assert created["approved"] is False


def test_a_report_for_a_future_date_rolls_back_to_the_previous_year(client):
    vessel_id = _create_vessel(client)
    tomorrow = date.today() + timedelta(days=1)
    disp_text = f"1 {tomorrow.strftime('%d%m')}/0800\n43 Мурманск\nNNNN"

    response = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": disp_text},
    )

    assert response.status_code == 201
    parsed_datetime = response.json()["report_datetime"]
    assert parsed_datetime.startswith(str(date.today().year - 1))


def test_duplicate_report_for_the_same_vessel_and_exact_datetime_is_rejected(client):
    vessel_id = _create_vessel(client)
    first = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01},
    )
    assert first.status_code == 201

    second = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01},
    )

    assert second.status_code == 409


def test_a_second_report_the_same_day_but_a_different_time_is_allowed(client):
    """A vessel can legitimately send more than one DISP-01 update on a busy
    port-operations day — the duplicate check must key on the exact reported
    datetime, not just the calendar date (confirmed against real historical
    data: distinct Message-IDs, distinct times, same day)."""
    vessel_id = _create_vessel(client)
    morning = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01},
    )
    assert morning.status_code == 201

    evening_text = SAMPLE_DISP01.replace("1 2705/0800", "1 2705/1400")
    evening = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": evening_text},
    )

    assert evening.status_code == 201


def test_operator_can_edit_a_report_before_approval(client):
    vessel_id = _create_vessel(client)
    report_id = client.post(
        "/daily-reports", json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]

    corrected_text = SAMPLE_DISP01.replace("43 Архангельск", "43 Мурманск")
    response = client.put(f"/daily-reports/{report_id}", json={"raw_text": corrected_text})

    assert response.status_code == 200
    assert response.json()["fields"]["43"] == "Мурманск"


def test_approved_report_cannot_be_edited_without_override(client):
    vessel_id = _create_vessel(client)
    report_id = client.post(
        "/daily-reports", json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]

    approve_response = client.post(f"/daily-reports/{report_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["approved"] is True

    blocked = client.put(f"/daily-reports/{report_id}", json={"raw_text": SAMPLE_DISP01})
    assert blocked.status_code == 409

    overridden = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "override": True},
    )
    assert overridden.status_code == 200


def test_operator_can_reassign_a_report_to_a_different_vessel(client):
    """Recovery path for exactly the accident that motivated this: a batch of
    reports gets ingested under the wrong vessel (e.g. an IMAP poll run against
    the wrong dropdown selection). The operator must be able to correct the
    vessel_id after the fact, through the normal audited edit path — not a raw
    database edit that would bypass the audit log."""
    wrong_vessel_id = _create_vessel(client)
    correct_vessel_id = client.post("/vessels", json=vessel_payload(imo_number="9000001")).json()["id"]
    report_id = client.post(
        "/daily-reports", json={"vessel_id": wrong_vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]

    response = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "vessel_id": correct_vessel_id},
    )

    assert response.status_code == 200
    assert response.json()["vessel_id"] == correct_vessel_id
    assert client.get(f"/daily-reports/{report_id}").json()["vessel_id"] == correct_vessel_id


def test_reassigning_to_a_vessel_with_a_conflicting_date_is_rejected(client):
    wrong_vessel_id = _create_vessel(client)
    correct_vessel_id = client.post("/vessels", json=vessel_payload(imo_number="9000002")).json()["id"]
    # the destination vessel already has a report for this same date
    client.post("/daily-reports", json={"vessel_id": correct_vessel_id, "raw_text": SAMPLE_DISP01})
    report_id = client.post(
        "/daily-reports", json={"vessel_id": wrong_vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]

    response = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "vessel_id": correct_vessel_id},
    )

    assert response.status_code == 409


def test_reassigning_to_an_unknown_vessel_returns_404(client):
    vessel_id = _create_vessel(client)
    report_id = client.post(
        "/daily-reports", json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]

    response = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "vessel_id": 999},
    )

    assert response.status_code == 404


def test_reassigning_an_approved_report_requires_override(client):
    wrong_vessel_id = _create_vessel(client)
    correct_vessel_id = client.post("/vessels", json=vessel_payload(imo_number="9000003")).json()["id"]
    report_id = client.post(
        "/daily-reports", json={"vessel_id": wrong_vessel_id, "raw_text": SAMPLE_DISP01}
    ).json()["id"]
    client.post(f"/daily-reports/{report_id}/approve")

    blocked = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "vessel_id": correct_vessel_id},
    )
    assert blocked.status_code == 409

    overridden = client.put(
        f"/daily-reports/{report_id}",
        json={"raw_text": SAMPLE_DISP01, "vessel_id": correct_vessel_id, "override": True},
    )
    assert overridden.status_code == 200
    assert overridden.json()["vessel_id"] == correct_vessel_id


def test_explicit_yyyy_mm_dd_date_line_is_used_directly_without_year_inference(client):
    """A years-old historical report re-entered manually must not be silently
    reinterpreted as this year or last year — the operator amends the date line
    to an explicit YYYY-MM-DD/HHMM format specifically to avoid that ambiguity."""
    vessel_id = _create_vessel(client)
    historical_text = "1 2022-05-27/0800\n43 Архангельск\nNNNN"

    response = client.post("/daily-reports", json={"vessel_id": vessel_id, "raw_text": historical_text})

    assert response.status_code == 201
    assert response.json()["report_datetime"] == "2022-05-27 08:00:00"


def test_explicit_date_line_also_accepts_a_colon_time_separator(client):
    vessel_id = _create_vessel(client)
    historical_text = "1 2022-05-27/08:00\n43 Архангельск\nNNNN"

    response = client.post("/daily-reports", json={"vessel_id": vessel_id, "raw_text": historical_text})

    assert response.status_code == 201
    assert response.json()["report_datetime"] == "2022-05-27 08:00:00"


def test_operator_can_list_daily_reports(client):
    vessel_id = _create_vessel(client)
    client.post("/daily-reports", json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01})

    response = client.get("/daily-reports")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["fields"]["43"] == "Архангельск"


def test_listing_daily_reports_can_be_filtered_by_vessel(client):
    vessel_id = _create_vessel(client)
    other_vessel_id = client.post(
        "/vessels", json=vessel_payload(imo_number="9999999")
    ).json()["id"]
    client.post("/daily-reports", json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01})
    client.post("/daily-reports", json={"vessel_id": other_vessel_id, "raw_text": SAMPLE_DISP01})

    response = client.get(f"/daily-reports?vessel_id={vessel_id}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["vessel_id"] == vessel_id
