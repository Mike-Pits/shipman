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


def test_duplicate_report_for_same_vessel_and_date_is_rejected(client):
    vessel_id = _create_vessel(client)
    first = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": SAMPLE_DISP01},
    )
    assert first.status_code == 201

    duplicate_text = SAMPLE_DISP01.replace("1 2705/0800", "1 2705/1400")
    second = client.post(
        "/daily-reports",
        json={"vessel_id": vessel_id, "raw_text": duplicate_text},
    )

    assert second.status_code == 409


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
