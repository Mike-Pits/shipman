from datetime import date, timedelta

from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _yesterday():
    return (date.today() - timedelta(days=1)).isoformat()


def _next_month():
    return (date.today() + timedelta(days=30)).isoformat()


def test_operator_can_record_an_inspection_and_it_appears_in_history(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
            "observations": "No major findings",
        },
    )
    assert response.status_code == 201

    history = client.get(f"/vessels/{vessel_id}/vetting-inspections")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_current_status_reflects_the_most_recent_inspection(client):
    vessel_id = _create_vessel(client)
    client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "failed",
        },
    )
    client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2026-06-01",
            "inspecting_body": "BP",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
        },
    )

    response = client.get(f"/vessels/{vessel_id}/vetting-status")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["inspecting_body"] == "BP"


def test_an_approved_inspection_past_its_expiry_shows_as_expired(client):
    vessel_id = _create_vessel(client)
    client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2025-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _yesterday(),
            "status": "approved",
        },
    )

    response = client.get(f"/vessels/{vessel_id}/vetting-status")

    assert response.json()["status"] == "expired"


def test_vessel_with_no_inspections_has_no_status(client):
    vessel_id = _create_vessel(client)

    response = client.get(f"/vessels/{vessel_id}/vetting-status")

    assert response.status_code == 200
    assert response.json()["status"] is None


def test_operator_can_correct_an_inspection_and_it_is_reflected_in_history_and_status(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
            "observations": "No major findings",
        },
    ).json()

    response = client.put(
        f"/vessels/{vessel_id}/vetting-inspections/{created['id']}",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "failed",
            "observations": "Corrected: 2 findings identified after review",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "failed"
    assert updated["observations"] == "Corrected: 2 findings identified after review"

    status_response = client.get(f"/vessels/{vessel_id}/vetting-status")
    assert status_response.json()["status"] == "failed"


def test_correcting_an_inspection_for_an_unknown_vessel_returns_404(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
        },
    ).json()

    response = client.put(
        f"/vessels/999999/vetting-inspections/{created['id']}",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
        },
    )

    assert response.status_code == 404


def test_correcting_an_inspection_that_does_not_belong_to_the_vessel_returns_404(client):
    vessel_a = client.post("/vessels", json=vessel_payload(imo_number="9111111")).json()["id"]
    vessel_b = client.post("/vessels", json=vessel_payload(imo_number="9222222")).json()["id"]
    created = client.post(
        f"/vessels/{vessel_a}/vetting-inspections",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
        },
    ).json()

    response = client.put(
        f"/vessels/{vessel_b}/vetting-inspections/{created['id']}",
        json={
            "inspection_date": "2026-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": _next_month(),
            "status": "approved",
        },
    )

    assert response.status_code == 404
