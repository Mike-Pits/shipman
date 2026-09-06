from tests.test_vessels import vessel_payload


def _create_vessel(client):
    return client.post("/vessels", json=vessel_payload()).json()["id"]


def test_bunker_cost_is_calculated_automatically_from_price_and_quantity(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "invoice_number": "INV-001",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 200, "price_per_mt": 550}],
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["lines"][0]["total_cost"] == 110000
    assert created["total_cost"] == 110000


def test_a_replenishment_event_can_cover_multiple_fuel_grades_priced_independently(client):
    vessel_id = _create_vessel(client)

    response = client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "invoice_number": "INV-002",
            "currency": "USD",
            "lines": [
                {"fuel_grade": "IFO", "quantity_mt": 200, "price_per_mt": 550},
                {"fuel_grade": "MGO", "quantity_mt": 30, "price_per_mt": 800},
            ],
        },
    )

    assert response.status_code == 201
    created = response.json()
    totals_by_grade = {line["fuel_grade"]: line["total_cost"] for line in created["lines"]}
    assert totals_by_grade == {"IFO": 110000, "MGO": 24000}
    assert created["total_cost"] == 134000


def test_operator_can_list_and_retrieve_bunker_replenishments(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "invoice_number": "INV-003",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 100, "price_per_mt": 500}],
        },
    ).json()

    list_response = client.get("/bunker-replenishments")
    assert list_response.status_code == 200
    assert any(r["id"] == created["id"] for r in list_response.json())

    get_response = client.get(f"/bunker-replenishments/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["supplier"] == "Baltic Bunker Co"


def test_operator_can_correct_a_bunker_replenishment_including_its_lines(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "invoice_number": "INV-004",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 200, "price_per_mt": 550}],
        },
    ).json()

    response = client.put(
        f"/bunker-replenishments/{created['id']}",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 12:00:00",
            "port": "Ust-Luga",
            "supplier": "Corrected Supplier Ltd",
            "invoice_number": "INV-004-CORRECTED",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 180, "price_per_mt": 540}],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["supplier"] == "Corrected Supplier Ltd"
    assert len(updated["lines"]) == 1
    assert updated["lines"][0]["quantity_mt"] == 180
    assert updated["total_cost"] == 97200


def test_correcting_a_bunker_replenishment_for_an_unknown_vessel_is_rejected(client):
    vessel_id = _create_vessel(client)
    created = client.post(
        "/bunker-replenishments",
        json={
            "vessel_id": vessel_id,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 200, "price_per_mt": 550}],
        },
    ).json()

    response = client.put(
        f"/bunker-replenishments/{created['id']}",
        json={
            "vessel_id": 999999,
            "replenishment_datetime": "2026-06-01 10:00:00",
            "port": "Ust-Luga",
            "supplier": "Baltic Bunker Co",
            "currency": "USD",
            "lines": [{"fuel_grade": "IFO", "quantity_mt": 200, "price_per_mt": 550}],
        },
    )

    assert response.status_code == 404
