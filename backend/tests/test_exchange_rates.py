from datetime import date

from app.dependencies import get_rate_fetcher
from app.main import app
from app.services.cbr_rate_fetcher import RateFetchError


def test_operator_can_fetch_and_store_todays_rate(client):
    app.dependency_overrides[get_rate_fetcher] = lambda: (lambda: 92.75)

    response = client.post("/exchange-rates/fetch")

    assert response.status_code == 200
    body = response.json()
    assert body["usd_rub_rate"] == 92.75
    assert body["rate_date"] == date.today().isoformat()
    assert body["stale"] is False

    app.dependency_overrides.pop(get_rate_fetcher, None)


def test_operator_can_retrieve_the_historical_rate_for_a_date(client):
    app.dependency_overrides[get_rate_fetcher] = lambda: (lambda: 91.10)
    client.post("/exchange-rates/fetch")
    app.dependency_overrides.pop(get_rate_fetcher, None)

    response = client.get(f"/exchange-rates/{date.today().isoformat()}")

    assert response.status_code == 200
    assert response.json()["usd_rub_rate"] == 91.10


def test_fetch_failure_falls_back_to_last_known_rate(client):
    app.dependency_overrides[get_rate_fetcher] = lambda: (lambda: 90.00)
    client.post("/exchange-rates/fetch")
    app.dependency_overrides.pop(get_rate_fetcher, None)

    def failing_fetcher():
        raise RateFetchError("network unreachable")

    app.dependency_overrides[get_rate_fetcher] = lambda: failing_fetcher
    response = client.post("/exchange-rates/fetch")
    app.dependency_overrides.pop(get_rate_fetcher, None)

    assert response.status_code == 200
    body = response.json()
    assert body["usd_rub_rate"] == 90.00
    assert body["stale"] is True


def test_fetch_failure_with_no_known_rate_returns_503(client):
    def failing_fetcher():
        raise RateFetchError("network unreachable")

    app.dependency_overrides[get_rate_fetcher] = lambda: failing_fetcher
    response = client.post("/exchange-rates/fetch")
    app.dependency_overrides.pop(get_rate_fetcher, None)

    assert response.status_code == 503


def test_operator_can_manually_override_a_rate_for_a_specific_date(client):
    override_response = client.put(
        "/exchange-rates/2026-05-01", json={"usd_rub_rate": 88.88}
    )

    assert override_response.status_code == 200
    body = override_response.json()
    assert body["usd_rub_rate"] == 88.88
    assert body["manual_override"] is True

    fetched = client.get("/exchange-rates/2026-05-01")
    assert fetched.json()["usd_rub_rate"] == 88.88
    assert fetched.json()["manual_override"] is True
