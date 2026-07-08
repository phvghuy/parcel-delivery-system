from tests.factories import make_truck


def test_list_trucks_empty(client):
    response = client.get("/trucks")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_truck_then_get(client):
    body = {
        "id": "22222222-2222-2222-2222-222222222222",
        "plate_number": "51A-999.99",
        "max_weight": 1000.0,
        "max_volume": 10.0,
    }
    create_resp = client.post("/trucks", json=body)
    assert create_resp.status_code == 201
    assert create_resp.json()["status"] == 1

    get_resp = client.get(f"/trucks/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["plate_number"] == "51A-999.99"


def test_create_truck_validation_error(client):
    body = {
        "id": "33333333-3333-3333-3333-333333333333",
        "plate_number": "",
        "max_weight": 1000.0,
        "max_volume": 10.0,
    }
    response = client.post("/trucks", json=body)
    assert response.status_code == 422


def test_create_truck_negative_weight_rejected_by_schema(client):
    body = {
        "id": "44444444-4444-4444-4444-444444444444",
        "plate_number": "51A-000.00",
        "max_weight": -1.0,
        "max_volume": 10.0,
    }
    response = client.post("/trucks", json=body)
    assert response.status_code == 422


def test_get_truck_not_found(client):
    response = client.get("/trucks/55555555-5555-5555-5555-555555555555")
    assert response.status_code == 404


def test_update_truck(client, fakes):
    truck = make_truck()
    fakes.truck_repo._store.append(truck)
    body = {
        "plate_number": "51A-111.11",
        "max_weight": truck.capacity.max_weight,
        "max_volume": truck.capacity.max_volume,
        "status": 2,
    }
    response = client.put(f"/trucks/{truck.id}", json=body)
    assert response.status_code == 200
    assert response.json()["plate_number"] == "51A-111.11"
    assert response.json()["status"] == 2


def test_delete_truck(client, fakes):
    truck = make_truck()
    fakes.truck_repo._store.append(truck)
    response = client.delete(f"/trucks/{truck.id}")
    assert response.status_code == 204
    assert client.get(f"/trucks/{truck.id}").status_code == 404


def test_delete_truck_not_found(client):
    response = client.delete("/trucks/66666666-6666-6666-6666-666666666666")
    assert response.status_code == 404
