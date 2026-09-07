from tests.test_vessels import vessel_payload


def estimate_payload(**overrides):
    payload = {
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
    }
    payload.update(overrides)
    return payload


def test_operator_can_create_an_estimate_with_computed_tce(client):
    response = client.post("/voyage-estimates", json=estimate_payload())

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "draft"
    # revenue = 30 * 5000 = 150000; costs = 110000 + 20000 = 130000; net = 20000; tce = 20000/10
    assert created["estimated_revenue"] == 150000
    assert created["estimated_costs"] == 130000
    assert created["estimated_net_result"] == 20000
    assert created["estimated_tce_per_day"] == 2000


def test_estimate_rejects_a_currency_other_than_rub_or_usd(client):
    response = client.post("/voyage-estimates", json=estimate_payload(currency="EUR"))

    assert response.status_code == 422


def test_operator_can_progress_an_estimate_through_negotiation_or_decline_it(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    negotiating = client.post(
        f"/voyage-estimates/{created['id']}/status", json={"status": "under_negotiation"}
    )
    assert negotiating.status_code == 200
    assert negotiating.json()["status"] == "under_negotiation"

    declined = client.post(
        f"/voyage-estimates/{created['id']}/status", json={"status": "declined"}
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"


def test_promoting_an_estimate_creates_a_linked_fixture_and_marks_it_fixed(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    response = client.post(
        f"/voyage-estimates/{created['id']}/promote",
        json={
            "fixture_type": "voyage_charter",
            "charterer": "Test Charterer",
            "contract_currency": "USD",
            "freight_rate": 30,
            "freight_rate_basis": "per_tonne",
            "load_port": "Ust-Luga",
            "discharge_port": "Rotterdam",
            "cargo_grade": "gasoil",
        },
    )

    assert response.status_code == 201
    fixture = response.json()
    assert fixture["fixture_type"] == "voyage_charter"

    updated_estimate = client.get(f"/voyage-estimates/{created['id']}").json()
    assert updated_estimate["status"] == "fixed"
    assert updated_estimate["fixture_id"] == fixture["id"]


def test_operator_can_list_and_retrieve_voyage_estimates(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    list_response = client.get("/voyage-estimates")
    assert list_response.status_code == 200
    assert any(e["id"] == created["id"] for e in list_response.json())

    get_response = client.get(f"/voyage-estimates/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["load_port"] == "Ust-Luga"


def test_operator_can_correct_an_estimate_and_its_computed_figures_update(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()

    response = client.put(
        f"/voyage-estimates/{created['id']}",
        json=estimate_payload(estimated_rate=35),
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["estimated_rate"] == 35
    # revenue = 35*5000 = 175000; costs = 130000; net = 45000
    assert updated["estimated_revenue"] == 175000
    assert updated["estimated_net_result"] == 45000


def test_correcting_an_estimate_preserves_its_status_and_fixture_link(client):
    created = client.post("/voyage-estimates", json=estimate_payload()).json()
    client.post(f"/voyage-estimates/{created['id']}/status", json={"status": "under_negotiation"})

    response = client.put(
        f"/voyage-estimates/{created['id']}",
        json=estimate_payload(estimated_rate=32),
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "under_negotiation"
    assert updated["fixture_id"] is None


def test_correcting_an_unknown_estimate_returns_404(client):
    response = client.put("/voyage-estimates/999999", json=estimate_payload())

    assert response.status_code == 404
