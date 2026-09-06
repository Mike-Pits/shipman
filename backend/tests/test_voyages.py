from tests.test_fixtures import voyage_charter_payload
from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def _create_fixture(client):
    return client.post("/fixtures", json=voyage_charter_payload()).json()["id"]


def voyage_payload(fixture_id, vessel_id, **overrides):
    payload = {
        "fixture_id": fixture_id,
        "vessel_id": vessel_id,
        "voyage_number": "V001",
        "load_port": "Primorsk",
        "discharge_port": "Rotterdam",
        "start_date": "2026-09-02",
        "end_date": "2026-09-14",
        "cargo_grade": "Diesel",
        "cargo_quantity_mt": 8200.0,
        "laden": True,
        "ice_notes": "",
    }
    payload.update(overrides)
    return payload


def test_operator_can_create_and_retrieve_a_voyage(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)

    create_response = client.post("/voyages", json=voyage_payload(fixture_id, vessel_id))

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] is not None
    assert created["voyage_number"] == "V001"
    assert created["fixture_id"] == fixture_id
    assert created["vessel_id"] == vessel_id

    fetched = client.get(f"/voyages/{created['id']}").json()
    assert fetched["load_port"] == "Primorsk"
    assert fetched["laden"] is True


def test_a_fixture_can_have_multiple_voyages_operator_defined_boundaries(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)

    # operator splits the itinerary into two separate port-to-port voyages
    client.post(
        "/voyages",
        json=voyage_payload(fixture_id, vessel_id, voyage_number="V001-LEG1", load_port="Primorsk", discharge_port="Kaliningrad"),
    )
    client.post(
        "/voyages",
        json=voyage_payload(fixture_id, vessel_id, voyage_number="V001-LEG2", load_port="Kaliningrad", discharge_port="Rotterdam"),
    )

    list_response = client.get(f"/voyages?fixture_id={fixture_id}")

    assert list_response.status_code == 200
    voyage_numbers = {v["voyage_number"] for v in list_response.json()}
    assert voyage_numbers == {"V001-LEG1", "V001-LEG2"}


def test_creating_a_voyage_for_an_unknown_fixture_returns_404(client):
    vessel_id = _create_vessel(client)

    response = client.post("/voyages", json=voyage_payload(fixture_id=999, vessel_id=vessel_id))

    assert response.status_code == 404


def test_operator_can_update_a_voyage(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)
    created = client.post("/voyages", json=voyage_payload(fixture_id, vessel_id)).json()

    response = client.put(
        f"/voyages/{created['id']}",
        json=voyage_payload(fixture_id, vessel_id, cargo_quantity_mt=9000.0),
    )

    assert response.status_code == 200
    assert response.json()["cargo_quantity_mt"] == 9000.0
    assert client.get(f"/voyages/{created['id']}").json()["cargo_quantity_mt"] == 9000.0


def test_updating_an_unknown_voyage_returns_404(client):
    vessel_id = _create_vessel(client)
    fixture_id = _create_fixture(client)

    response = client.put("/voyages/999", json=voyage_payload(fixture_id, vessel_id))

    assert response.status_code == 404
