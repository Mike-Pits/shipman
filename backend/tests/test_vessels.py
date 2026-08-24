def vessel_payload(**overrides):
    payload = {
        "name": "SP Baltic Trader",
        "imo_number": "9123456",
        "flag": "Russia",
        "year_built": 2015,
        "vessel_type": "clean/product tanker",
        "dwt": 8500.0,
        "loa": 120.5,
        "beam": 18.2,
        "draft": 7.1,
        "cargo_tank_capacity_cbm": 9800.0,
        "ice_class": "Arc4",
        "engine_power_kw": 4500.0,
        "fuel_consumption_profiles": [
            {"mode": "laden", "ifo_mt_per_day": 18.5, "mgo_mt_per_day": 0.5},
            {"mode": "ballast", "ifo_mt_per_day": 16.0, "mgo_mt_per_day": 0.5},
            {"mode": "idle_anchor", "ifo_mt_per_day": 2.0, "mgo_mt_per_day": 0.2},
            {"mode": "discharging", "ifo_mt_per_day": 3.5, "mgo_mt_per_day": 1.0},
        ],
    }
    payload.update(overrides)
    return payload


def test_operator_can_register_and_retrieve_a_vessel(client):
    create_response = client.post("/vessels", json=vessel_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] is not None
    assert created["name"] == "SP Baltic Trader"
    assert created["imo_number"] == "9123456"

    get_response = client.get(f"/vessels/{created['id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["name"] == "SP Baltic Trader"
    assert fetched["imo_number"] == "9123456"


def test_operator_can_list_registered_vessels(client):
    client.post("/vessels", json=vessel_payload(name="SP Baltic Trader", imo_number="9123456"))
    client.post("/vessels", json=vessel_payload(name="SP Northern Star", imo_number="9234567"))

    list_response = client.get("/vessels")

    assert list_response.status_code == 200
    names = {v["name"] for v in list_response.json()}
    assert names == {"SP Baltic Trader", "SP Northern Star"}


def test_vessel_record_carries_ice_class_and_fuel_consumption_by_mode(client):
    created = client.post("/vessels", json=vessel_payload()).json()

    fetched = client.get(f"/vessels/{created['id']}").json()

    assert fetched["ice_class"] == "Arc4"
    profiles_by_mode = {p["mode"]: p for p in fetched["fuel_consumption_profiles"]}
    assert profiles_by_mode.keys() == {"laden", "ballast", "idle_anchor", "discharging"}
    assert profiles_by_mode["discharging"]["ifo_mt_per_day"] == 3.5
    assert profiles_by_mode["discharging"]["mgo_mt_per_day"] == 1.0


def test_operator_can_update_a_vessel_record(client):
    created = client.post("/vessels", json=vessel_payload()).json()

    update_response = client.put(
        f"/vessels/{created['id']}", json=vessel_payload(ice_class="Arc7")
    )

    assert update_response.status_code == 200
    assert update_response.json()["ice_class"] == "Arc7"
    assert client.get(f"/vessels/{created['id']}").json()["ice_class"] == "Arc7"


def test_updating_an_unknown_vessel_returns_404(client):
    response = client.put("/vessels/999", json=vessel_payload())

    assert response.status_code == 404
