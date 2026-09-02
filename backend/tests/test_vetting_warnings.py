from datetime import date, timedelta

from tests.test_vessels import vessel_payload


def _create_vessel_with_expired_vetting(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post(
        f"/vessels/{vessel_id}/vetting-inspections",
        json={
            "inspection_date": "2025-01-15",
            "inspecting_body": "Shell SIRE",
            "inspection_type": "SIRE",
            "expiry_date": yesterday,
            "status": "approved",
        },
    )
    return vessel_id


def _create_fixture(client):
    return client.post(
        "/fixtures",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 25.0,
            "freight_rate_basis": "per_tonne",
        },
    ).json()["id"]


def test_creating_a_voyage_for_a_vessel_with_expired_vetting_is_flagged(client):
    fixture_id = _create_fixture(client)
    expired_vessel_id = _create_vessel_with_expired_vetting(client)

    response = client.post(
        "/voyages",
        json={
            "fixture_id": fixture_id,
            "vessel_id": expired_vessel_id,
            "voyage_number": "V-001",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "start_date": "2026-06-01",
            "cargo_grade": "gasoil",
            "cargo_quantity_mt": 5000,
            "laden": True,
        },
    )

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1
    assert "vetting" in response.json()["warnings"][0].lower()


def test_creating_a_voyage_for_a_vessel_with_no_vetting_history_is_not_flagged(client):
    vessel_id = client.post("/vessels", json=vessel_payload()).json()["id"]
    fixture_id = _create_fixture(client)

    response = client.post(
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
    )

    assert response.json()["warnings"] == []


def test_voyage_estimate_with_an_expired_vetting_vessel_is_flagged(client):
    expired_vessel_id = _create_vessel_with_expired_vetting(client)

    response = client.post(
        "/voyage-estimates",
        json={
            "vessel_id": expired_vessel_id,
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "laycan_start": "2026-06-01",
            "laycan_end": "2026-06-05",
            "cargo_grade": "gasoil",
            "estimated_cargo_quantity_mt": 5000,
            "estimated_rate": 30,
            "estimated_rate_basis": "per_tonne",
            "currency": "USD",
            "estimated_bunker_consumption_mt": 200,
            "estimated_bunker_cost": 110000,
            "estimated_port_costs": 20000,
            "estimated_duration_days": 10,
        },
    )

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


def test_voyage_estimate_with_no_vessel_assigned_is_not_flagged(client):
    response = client.post(
        "/voyage-estimates",
        json={
            "vessel_id": None,
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "laycan_start": "2026-06-01",
            "laycan_end": "2026-06-05",
            "cargo_grade": "gasoil",
            "estimated_cargo_quantity_mt": 5000,
            "estimated_rate": 30,
            "estimated_rate_basis": "per_tonne",
            "currency": "USD",
            "estimated_bunker_consumption_mt": 200,
            "estimated_bunker_cost": 110000,
            "estimated_port_costs": 20000,
            "estimated_duration_days": 10,
        },
    )

    assert response.json()["warnings"] == []
