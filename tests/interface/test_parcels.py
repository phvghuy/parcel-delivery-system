from tests.factories import make_parcel


def test_list_parcels_empty(client):
    response = client.get("/parcels")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_get_parcel(client, fakes):
    parcel = make_parcel()
    fakes.parcel_repo._store.append(parcel)
    response = client.get(f"/parcels/{parcel.id}")
    assert response.status_code == 200
    assert response.json()["tracking_number"] == parcel.tracking_number


def test_get_parcel_not_found(client):
    response = client.get("/parcels/22222222-2222-2222-2222-222222222222")
    assert response.status_code == 404


def test_list_tracking_events(client, fakes):
    from smart_delivery_routing.domain.tracking.models import TrackingEvent, TrackingLocation, TrackingLocationType
    from smart_delivery_routing.domain.linehaul import ParcelStatus
    from uuid import uuid4
    from datetime import datetime, timezone

    parcel = make_parcel()
    fakes.parcel_repo._store.append(parcel)
    event = TrackingEvent(
        id=uuid4(),
        parcel_id=parcel.id,
        status=ParcelStatus.AWAITING_PICKUP,
        location=TrackingLocation(kind=TrackingLocationType.SYSTEM, name="System"),
        created_at=datetime.now(timezone.utc),
    )
    fakes.tracking_repo.events.append(event)

    response = client.get(f"/parcels/{parcel.id}/tracking-events")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_tracking_events_parcel_not_found(client):
    response = client.get("/parcels/33333333-3333-3333-3333-333333333333/tracking-events")
    assert response.status_code == 404
