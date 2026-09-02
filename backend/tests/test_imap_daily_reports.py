import pytest

from app.dependencies import get_imap_fetcher
from app.main import app
from tests.test_vessels import vessel_payload

VALID_MESSAGE_1 = "1 2705/0800\n43 Архангельск\nNNNN"
VALID_MESSAGE_2 = "1 2805/0800\n43 Мурманск\nNNNN"
MALFORMED_MESSAGE = "43 Мурманск\nNNNN"  # missing code 1 (date/time) — required


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _override_imap(messages: list[tuple[str, str]]):
    app.dependency_overrides[get_imap_fetcher] = lambda: (lambda folder: messages)


@pytest.fixture(autouse=True)
def _clear_imap_override():
    yield
    app.dependency_overrides.pop(get_imap_fetcher, None)


def test_polling_ingests_new_disp01_messages_found_via_imap(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1), ("msg-2", VALID_MESSAGE_2)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    assert response.status_code == 200
    body = response.json()
    assert len(body["ingested"]) == 2
    assert body["ingested"][0]["source_message_id"] == "msg-1"
    assert body["skipped_duplicates"] == []
    assert body["errors"] == []


def test_polling_again_does_not_duplicate_already_ingested_messages(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1), ("msg-2", VALID_MESSAGE_2)])
    client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    body = response.json()
    assert body["ingested"] == []
    assert set(body["skipped_duplicates"]) == {"msg-1", "msg-2"}


def test_a_message_that_fails_to_parse_is_reported_without_blocking_the_batch(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1), ("msg-bad", MALFORMED_MESSAGE)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    body = response.json()
    assert len(body["ingested"]) == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["message_id"] == "msg-bad"


def test_ingested_reports_go_through_the_same_parser_as_manual_entry(client):
    vessel_id = _create_vessel(client)
    _override_imap([("msg-1", VALID_MESSAGE_1)])

    response = client.post("/daily-reports/poll-imap", json={"vessel_id": vessel_id})

    ingested = response.json()["ingested"][0]
    assert ingested["report_datetime"] == "2026-05-27 08:00:00"
    assert ingested["fields"]["43"] == "Архангельск"
    assert ingested["approved"] is False


def test_operator_can_view_and_change_the_configured_mailbox_folder(client):
    client.put("/daily-reports/imap-settings", json={"folder": "DailyReports"})

    response = client.get("/daily-reports/imap-settings")

    assert response.status_code == 200
    assert response.json()["folder"] == "DailyReports"
