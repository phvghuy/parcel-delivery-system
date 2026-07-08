from tests.factories import make_driver


def test_list_drivers_empty(client):
    response = client.get("/drivers")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_driver_then_get(client, fakes):
    hub_id = "22222222-2222-2222-2222-222222222222"
    body = {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Nguyen Van A",
        "phone": "0901234567",
        "plate_number": "59H1-12345",
        "current_hub_id": hub_id,
        "max_weight": 100.0,
        "max_volume": 1.0,
    }
    create_resp = client.post("/drivers", json=body)
    assert create_resp.status_code == 201
    assert create_resp.json()["status"] == 1

    get_resp = client.get(f"/drivers/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["phone"] == "0901234567"


def test_create_driver_invalid_phone(client):
    body = {
        "id": "44444444-4444-4444-4444-444444444444",
        "name": "Nguyen Van A",
        "phone": "not-a-phone",
        "plate_number": "59H1-12345",
        "current_hub_id": "22222222-2222-2222-2222-222222222222",
        "max_weight": 100.0,
        "max_volume": 1.0,
    }
    response = client.post("/drivers", json=body)
    assert response.status_code == 422


def test_get_driver_not_found(client):
    response = client.get("/drivers/55555555-5555-5555-5555-555555555555")
    assert response.status_code == 404


def test_update_driver(client, fakes):
    driver = make_driver()
    fakes.driver_repo._store.append(driver)
    body = {
        "name": "Nguyen Van B",
        "phone": driver.profile.phone,
        "plate_number": driver.profile.plate_number,
        "current_hub_id": str(driver.current_hub_id),
        "max_weight": driver.capacity.max_weight,
        "max_volume": driver.capacity.max_volume,
        "status": 3,
    }
    response = client.put(f"/drivers/{driver.id}", json=body)
    assert response.status_code == 200
    assert response.json()["name"] == "Nguyen Van B"
    assert response.json()["status"] == 3


def test_delete_driver(client, fakes):
    driver = make_driver()
    fakes.driver_repo._store.append(driver)
    response = client.delete(f"/drivers/{driver.id}")
    assert response.status_code == 204
    assert client.get(f"/drivers/{driver.id}").status_code == 404


def test_delete_driver_not_found(client):
    response = client.delete("/drivers/66666666-6666-6666-6666-666666666666")
    assert response.status_code == 404


def test_update_fcm_token(client, fakes):
    from tests.interface.conftest import DEFAULT_DRIVER_ID
    from uuid import UUID

    driver = make_driver(id=UUID(DEFAULT_DRIVER_ID))
    fakes.driver_repo._store.append(driver)
    response = client.post("/drivers/fcm-token", json={"fcm_token": "new-token"})
    assert response.status_code == 204
    assert fakes.driver_repo._store[0].fcm_token == "new-token"
