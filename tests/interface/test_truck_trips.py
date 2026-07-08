from datetime import datetime, timezone

from smart_delivery_routing.domain.linehaul.models import ParcelStatus, TruckTripStatus
from tests.factories import make_parcel, make_truck, make_truck_trip


def test_list_truck_trips_empty(client):
    response = client.get("/truck-trips")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_truck_trip(client):
    body = {
        "truck_id": "22222222-2222-2222-2222-222222222222",
        "origin_hub_id": "33333333-3333-3333-3333-333333333333",
        "destination_hub_id": "44444444-4444-4444-4444-444444444444",
        "planned_departure_time": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/truck-trips", json=body)
    assert response.status_code == 201
    assert response.json()["status"] == TruckTripStatus.PLANNED.value


def test_create_truck_trip_same_hub_rejected(client):
    body = {
        "truck_id": "22222222-2222-2222-2222-222222222222",
        "origin_hub_id": "33333333-3333-3333-3333-333333333333",
        "destination_hub_id": "33333333-3333-3333-3333-333333333333",
        "planned_departure_time": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/truck-trips", json=body)
    assert response.status_code == 422


def test_get_truck_trip_not_found(client):
    response = client.get("/truck-trips/55555555-5555-5555-5555-555555555555")
    assert response.status_code == 404


def test_delete_planned_trip(client, fakes):
    trip = make_truck_trip()
    fakes.truck_trip_repo._store.append(trip)
    response = client.delete(f"/truck-trips/{trip.id}")
    assert response.status_code == 204


def test_delete_departed_trip_not_deletable(client, fakes):
    trip = make_truck_trip(status=TruckTripStatus.DEPARTED)
    fakes.truck_trip_repo._store.append(trip)
    response = client.delete(f"/truck-trips/{trip.id}")
    assert response.status_code == 409


def test_depart_and_arrive_trip(client, fakes):
    truck = make_truck()
    trip = make_truck_trip(truck_id=truck.id, status=TruckTripStatus.PLANNED)
    fakes.truck_repo._store.append(truck)
    fakes.truck_trip_repo._store.append(trip)

    depart_resp = client.post(f"/truck-trips/{trip.id}/depart")
    assert depart_resp.status_code == 200
    assert depart_resp.json()["status"] == TruckTripStatus.DEPARTED.value

    arrive_resp = client.post(f"/truck-trips/{trip.id}/arrive")
    assert arrive_resp.status_code == 200
    assert arrive_resp.json()["status"] == TruckTripStatus.ARRIVED.value


def test_depart_trip_not_planned_conflict(client, fakes):
    trip = make_truck_trip(status=TruckTripStatus.ARRIVED)
    fakes.truck_trip_repo._store.append(trip)
    response = client.post(f"/truck-trips/{trip.id}/depart")
    assert response.status_code == 409


def test_depart_trip_not_found(client):
    response = client.post("/truck-trips/66666666-6666-6666-6666-666666666666/depart")
    assert response.status_code == 404


def test_add_parcel_to_trip_and_list_items(client, fakes):
    trip = make_truck_trip()
    truck = make_truck(id=trip.truck_id)
    parcel = make_parcel(
        origin_hub_id=trip.origin_hub_id,
        destination_hub_id=trip.destination_hub_id,
        status=ParcelStatus.AT_ORIGIN_HUB,
    )
    fakes.truck_trip_repo._store.append(trip)
    fakes.truck_repo._store.append(truck)
    fakes.parcel_repo._store.append(parcel)

    add_resp = client.post(f"/truck-trips/{trip.id}/items", json={"parcel_id": str(parcel.id)})
    assert add_resp.status_code == 201
    item_id = add_resp.json()["id"]

    list_resp = client.get(f"/truck-trips/{trip.id}/items")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["tracking_number"] == parcel.tracking_number

    remove_resp = client.delete(f"/truck-trips/{trip.id}/items/{item_id}")
    assert remove_resp.status_code == 204


def test_add_parcel_to_trip_wrong_status_rejected(client, fakes):
    trip = make_truck_trip()
    truck = make_truck(id=trip.truck_id)
    parcel = make_parcel(
        origin_hub_id=trip.origin_hub_id,
        destination_hub_id=trip.destination_hub_id,
        status=ParcelStatus.AWAITING_PICKUP,
    )
    fakes.truck_trip_repo._store.append(trip)
    fakes.truck_repo._store.append(truck)
    fakes.parcel_repo._store.append(parcel)

    response = client.post(f"/truck-trips/{trip.id}/items", json={"parcel_id": str(parcel.id)})
    assert response.status_code == 422


def test_add_parcel_to_trip_parcel_not_found(client, fakes):
    trip = make_truck_trip()
    fakes.truck_trip_repo._store.append(trip)
    response = client.post(
        f"/truck-trips/{trip.id}/items", json={"parcel_id": "77777777-7777-7777-7777-777777777777"}
    )
    assert response.status_code == 404
