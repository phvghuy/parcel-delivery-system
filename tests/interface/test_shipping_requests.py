from tests.factories import make_shipping_request


VALID_BODY = {
    "id": "22222222-2222-2222-2222-222222222222",
    "external_order_id": "ORD-1000",
    "seller_id": "33333333-3333-3333-3333-333333333333",
    "pickup_address_text": "123 Nguyen Hue, Q1, TP.HCM",
    "pickup_lat": 10.7769,
    "pickup_lng": 106.7009,
    "delivery_address_text": "456 Le Loi, Q3, TP.HCM",
    "delivery_lat": 10.78,
    "delivery_lng": 106.71,
    "receiver_name": "Nguyen Van A",
    "receiver_phone": "0901234567",
    "weight": 2.0,
    "volume": 0.1,
    "service_type": 1,
}


def test_list_shipping_requests_empty(client):
    response = client.get("/shipping-requests")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_create_shipping_request_enqueues_job(client, fakes):
    response = client.post("/shipping-requests", json=VALID_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["external_order_id"] == "ORD-1000"
    assert body["status"] == 1  # CREATED
    assert len(fakes.job_service.enqueued_request_ids) == 1


def test_create_shipping_request_validation_error(client):
    body = {**VALID_BODY, "id": "44444444-4444-4444-4444-444444444444", "receiver_phone": "invalid"}
    response = client.post("/shipping-requests", json=body)
    assert response.status_code == 422


def test_get_shipping_request(client, fakes):
    request = make_shipping_request()
    fakes.shipping_request_repo._store.append(request)
    response = client.get(f"/shipping-requests/{request.id}")
    assert response.status_code == 200
    assert response.json()["external_order_id"] == request.external_order_id


def test_get_shipping_request_not_found(client):
    response = client.get("/shipping-requests/55555555-5555-5555-5555-555555555555")
    assert response.status_code == 404


def test_update_shipping_status(client, fakes):
    request = make_shipping_request()
    fakes.shipping_request_repo._store.append(request)
    response = client.patch(f"/shipping-requests/{request.id}/status", params={"status": 2})
    assert response.status_code == 204
    assert fakes.shipping_request_repo._store[0].status.value == 2


def test_update_shipping_status_invalid_transition(client, fakes):
    from smart_delivery_routing.domain.shipping.models import ShippingRequestStatus

    request = make_shipping_request(status=ShippingRequestStatus.REJECTED)
    fakes.shipping_request_repo._store.append(request)
    response = client.patch(f"/shipping-requests/{request.id}/status", params={"status": 2})
    assert response.status_code == 422


def test_update_shipping_status_not_found(client):
    response = client.patch(
        "/shipping-requests/66666666-6666-6666-6666-666666666666/status", params={"status": 2}
    )
    assert response.status_code == 404
