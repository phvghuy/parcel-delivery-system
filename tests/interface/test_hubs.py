from tests.factories import make_hub


def test_list_hubs_empty(client):
    response = client.get("/hubs")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20, "pages": 1}


def test_create_hub_then_list_and_get(client):
    body = {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Hub Q1",
        "type": 1,
        "address_text": "123 Nguyen Hue, Q1",
        "lat": 10.7769,
        "lng": 106.7009,
    }
    create_resp = client.post("/hubs", json=body)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] == body["id"]
    assert created["status"] == 1

    list_resp = client.get("/hubs")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    get_resp = client.get(f"/hubs/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Hub Q1"


def test_create_hub_validation_error(client):
    body = {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "",
        "type": 1,
        "address_text": "123 Nguyen Hue, Q1",
        "lat": 10.7769,
        "lng": 106.7009,
    }
    response = client.post("/hubs", json=body)
    assert response.status_code == 422


def test_get_hub_not_found(client):
    response = client.get("/hubs/44444444-4444-4444-4444-444444444444")
    assert response.status_code == 404


def test_update_hub(client, fakes):
    hub = make_hub()
    fakes.hub_repo._store.append(hub)
    body = {
        "name": "Hub Renamed",
        "type": hub.type.value,
        "address_text": hub.address.text,
        "lat": hub.address.location.lat,
        "lng": hub.address.location.lng,
        "status": 0,
    }
    response = client.put(f"/hubs/{hub.id}", json=body)
    assert response.status_code == 200
    assert response.json()["name"] == "Hub Renamed"
    assert response.json()["status"] == 0


def test_update_hub_not_found(client):
    body = {
        "name": "X",
        "type": 1,
        "address_text": "Y",
        "lat": 10.0,
        "lng": 106.0,
        "status": 1,
    }
    response = client.put("/hubs/55555555-5555-5555-5555-555555555555", json=body)
    assert response.status_code == 404


def test_delete_hub(client, fakes):
    hub = make_hub()
    fakes.hub_repo._store.append(hub)
    response = client.delete(f"/hubs/{hub.id}")
    assert response.status_code == 204
    assert client.get(f"/hubs/{hub.id}").status_code == 404


def test_delete_hub_not_found(client):
    response = client.delete("/hubs/66666666-6666-6666-6666-666666666666")
    assert response.status_code == 404


def test_hubs_require_auth(client):
    from smart_delivery_routing.interface.api import app, dependencies as deps

    del app.dependency_overrides[deps.require_admin]
    try:
        response = client.get("/hubs")
        assert response.status_code == 401
    finally:
        app.dependency_overrides[deps.require_admin] = lambda: None
