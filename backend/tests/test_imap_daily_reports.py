from datetime import datetime

import pytest

from app.dependencies import get_imap_fetcher
from app.main import app
from tests.test_vessels import vessel_payload

VALID_MESSAGE_1 = "1 2705/0800\n43 Архангельск\nNNNN"
VALID_MESSAGE_2 = "1 2805/0800\n43 Мурманск\nNNNN"
MALFORMED_MESSAGE = "43 Мурманск\nNNNN"  # missing code 1 (date/time) — required


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _override_imap(messages: list[tuple[str, str, datetime | None]]):
    """messages: (message_id, body, email_date) — email_date is the message's own
    envelope date, used to resolve the year for archived/historical messages whose
    DISP-01 body only carries day/month (see FR-16 year-resolution fix)."""
    app.dependency_overrides[get_imap_fetcher] = lambda: (lambda folder: messages)


@pytest.fixture(autouse=True)
def _clear_imap_override():
    yield
    app.dependency_overrides.pop(get_imap_fetcher, None)


def test_polling_ingests_new_disp01_messages_found_via_imap(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1, None), ("msg-2", VALID_MESSAGE_2, None)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    assert response.status_code == 200
    body = response.json()
    assert len(body["ingested"]) == 2
    assert body["ingested"][0]["source_message_id"] == "msg-1"
    assert body["skipped_duplicates"] == []
    assert body["errors"] == []


def test_polling_again_does_not_duplicate_already_ingested_messages(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1, None), ("msg-2", VALID_MESSAGE_2, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    body = response.json()
    assert body["ingested"] == []
    assert set(body["skipped_duplicates"]) == {"msg-1", "msg-2"}


def test_a_message_that_fails_to_parse_is_reported_without_blocking_the_batch(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1, None), ("msg-bad", MALFORMED_MESSAGE, None)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    body = response.json()
    assert len(body["ingested"]) == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["message_id"] == "msg-bad"


def test_ingested_reports_go_through_the_same_parser_as_manual_entry(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    ingested = response.json()["ingested"][0]
    assert ingested["report_datetime"] == "2026-05-27 08:00:00"
    assert ingested["fields"]["43"] == "Архангельск"
    assert ingested["approved"] is False


def test_ingested_reports_resolve_year_from_the_emails_own_date_not_todays_date(client):
    """The DISP-01 body only carries day/month (e.g. "2705" = 27 May), so for an
    archived historical message (year(s) old) there is no way to recover the year
    from the body alone. The email's own envelope date is the trusted anchor —
    resolution must use that, not the server's current date."""
    vessel_id = _create_vessel(client)
    archived_message = "1 2705/0800\n43 Архангельск\nNNNN"
    email_sent_at = datetime(2022, 5, 28, 10, 0, 0)  # the day after the report, in 2022
    _override_imap([("msg-old", archived_message, email_sent_at)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    assert response.status_code == 200
    ingested = response.json()["ingested"][0]
    assert ingested["report_datetime"] == "2022-05-27 08:00:00"


def test_operator_can_view_and_change_the_configured_mailbox_folder(client):
    client.put("/daily-reports/imap-settings", json={"folder": "DailyReports"})

    response = client.get("/daily-reports/imap-settings")

    assert response.status_code == 200
    assert response.json()["folder"] == "DailyReports"


def _vessel(client, imo="9000000"):
    return client.post("/vessels", json=vessel_payload(imo_number=imo)).json()["id"]


def test_first_poll_of_a_folder_establishes_its_vessel_mapping(client):
    vessel_a = _vessel(client, "9000001")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    assert response.status_code == 200
    assert len(response.json()["ingested"]) == 1


def test_repolling_the_same_folder_for_the_same_vessel_is_unaffected(client):
    vessel_a = _vessel(client, "9000002")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    _override_imap([("msg-2", VALID_MESSAGE_2, None)])
    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    assert response.status_code == 200
    assert len(response.json()["ingested"]) == 1


def test_polling_a_known_folder_under_a_different_vessel_is_blocked(client):
    """The exact accident this safeguard exists for: a folder known to hold one
    vessel's reports gets polled with a different vessel selected in the dropdown."""
    vessel_a = _vessel(client, "9000003")
    vessel_b = _vessel(client, "9000004")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    _override_imap([("msg-2", VALID_MESSAGE_2, None)])
    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_b})

    assert response.status_code == 409
    assert str(vessel_a) in response.json()["detail"]


def test_polling_a_known_folder_under_a_different_vessel_succeeds_with_confirmation(client):
    vessel_a = _vessel(client, "9000005")
    vessel_b = _vessel(client, "9000006")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    _override_imap([("msg-2", VALID_MESSAGE_2, None)])
    response = client.post(
        "/daily-reports/poll-imap",
        json={"vessel_id": vessel_b, "confirm_vessel_change": True},
    )

    assert response.status_code == 200
    assert len(response.json()["ingested"]) == 1


def test_confirmed_vessel_change_updates_the_remembered_mapping(client):
    vessel_a = _vessel(client, "9000007")
    vessel_b = _vessel(client, "9000008")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})
    _override_imap([("msg-2", VALID_MESSAGE_2, None)])
    client.post(
        "/daily-reports/poll-imap",
        json={"vessel_id": vessel_b, "confirm_vessel_change": True},
    )

    # now the folder is mapped to vessel_b — polling under vessel_a again should
    # itself be blocked without confirmation, proving the mapping really updated
    _override_imap([("msg-3", MALFORMED_MESSAGE, None)])
    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    assert response.status_code == 409
    assert str(vessel_b) in response.json()["detail"]


def test_operator_can_check_a_folders_mapped_vessel_before_polling(client):
    vessel_a = _vessel(client, "9000009")
    client.put("/daily-reports/imap-settings", json={"folder": "VesselA-2026"})
    _override_imap([("msg-1", VALID_MESSAGE_1, None)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_a})

    response = client.get("/daily-reports/imap-folder-mapping/VesselA-2026")

    assert response.status_code == 200
    assert response.json()["vessel_id"] == vessel_a


def test_checking_the_mapping_for_an_unpolled_folder_returns_404(client):
    response = client.get("/daily-reports/imap-folder-mapping/NeverPolledFolder")

    assert response.status_code == 404
