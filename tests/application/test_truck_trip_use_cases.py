from uuid import uuid4
from datetime import datetime, timezone
import pytest

from tests.fakes import FakeParcelRepo, FakeTrackingRepo, FakeTruckRepo, FakeTruckTripRepo, FakeTruckTripItemRepo
from tests.factories import make_parcel, make_truck, make_truck_trip
from smart_delivery_routing.domain.linehaul import TruckTripStatus, ParcelStatus, TruckTripItem
from smart_delivery_routing.domain.shared import Capacity, Load
from smart_delivery_routing.application.truck_trip_use_cases import (
    create_truck_trip,
    get_truck_trip,
    depart_trip,
    arrive_trip,
    delete_truck_trip,
    add_parcel_to_trip,
    remove_parcel_from_trip,
    TruckStatus,
    ValidationFailed,
    TruckTripNotFound,
    TruckTripCannotDepart,
    TruckTripCannotArrive,
    TruckTripNotDeletable,
    ParcelNotFound,
    InvalidParcelForTrip,
    CapacityExceeded,
    TruckTripItemNotFound,
    TruckTripItemNotRemovable,
)


# Create Truck Trip

def test_create_truck_trip_status_is_planned():
    result = create_truck_trip(
        truck_id=uuid4(),
        origin_hub_id=uuid4(),
        destination_hub_id=uuid4(),
        planned_departure_time=datetime.now(timezone.utc),
        repo=FakeTruckTripRepo(),
    )

    assert result.status == TruckTripStatus.PLANNED

def test_create_truck_trip_raises_validation_failed_when_same_hub():
    hub_id = uuid4()

    with pytest.raises(ValidationFailed):
        create_truck_trip(
            truck_id=uuid4(),
            origin_hub_id=hub_id,
            destination_hub_id=hub_id,
            planned_departure_time=datetime.now(timezone.utc),
            repo=FakeTruckTripRepo(),
        )


# Get Truck Trip

def test_get_truck_trip_returns_existing_trip():
    trip_repo = FakeTruckTripRepo()
    trip = make_truck_trip()
    trip_repo.create(trip)

    result = get_truck_trip(trip.id, trip_repo)

    assert result.id == trip.id

def test_get_truck_trip_raises_not_found_when_missing():
    trip_repo = FakeTruckTripRepo()

    with pytest.raises(TruckTripNotFound):
        get_truck_trip(trip_id=uuid4(), repo=trip_repo)


# Depart Trip

@pytest.mark.anyio
async def test_depart_trip_transitions_to_departed():
    trip_repo = FakeTruckTripRepo()
    trip = make_truck_trip()
    trip_repo.create(trip)
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    result = await depart_trip(
        trip_id=trip.id,
        trip_repo=trip_repo,
        item_repo=item_repo,
        parcel_repo=parcel_repo,
        truck_repo=FakeTruckRepo(),
        tracking_repo=FakeTrackingRepo(),
    )

    assert result.status == TruckTripStatus.DEPARTED

@pytest.mark.anyio
async def test_depart_trip_raises_not_found_when_missing():
    with pytest.raises(TruckTripNotFound):
        await depart_trip(
            trip_id=uuid4(),
            trip_repo=FakeTruckTripRepo(),
            item_repo=FakeTruckTripItemRepo(FakeParcelRepo()),
            parcel_repo=FakeParcelRepo(),
            truck_repo=FakeTruckRepo(),
            tracking_repo=FakeTrackingRepo(),
        )

@pytest.mark.anyio
async def test_depart_trip_raises_cannot_depart_when_already_departed():
    trip_repo = FakeTruckTripRepo()
    trip = make_truck_trip(status=TruckTripStatus.DEPARTED)
    trip_repo.create(trip)
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    with pytest.raises(TruckTripCannotDepart):
        await depart_trip(
            trip_id=trip.id,
            trip_repo=trip_repo,
            item_repo=item_repo,
            parcel_repo=parcel_repo,
            truck_repo=FakeTruckRepo(),
            tracking_repo=FakeTrackingRepo(),
        )

@pytest.mark.anyio
async def test_depart_trip_updates_truck_status_to_in_transit():
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)
    truck_repo = FakeTruckRepo()
    truck = make_truck()
    truck_repo.create(truck)
    trip = make_truck_trip(truck_id=truck.id)
    trip_repo.create(trip)

    await depart_trip(
        trip_id=trip.id,
        trip_repo=trip_repo,
        item_repo=item_repo,
        parcel_repo=parcel_repo,
        truck_repo=truck_repo,
        tracking_repo=FakeTrackingRepo(),
    )

    updated_truck = truck_repo.get_by_id(truck.id)
    assert updated_truck.status == TruckStatus.IN_TRANSIT

@pytest.mark.anyio
async def test_depart_trip_dispatches_parcels_in_trip():
    trip_repo = FakeTruckTripRepo()
    truck_repo = FakeTruckRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)
    tracking_repo = FakeTrackingRepo()

    truck = make_truck()
    truck_repo.create(truck)

    trip = make_truck_trip(truck_id=truck.id)
    trip_repo.create(trip)

    parcels = [make_parcel(status=ParcelStatus.AT_ORIGIN_HUB) for _ in range(5)]
    for parcel in parcels:
        await parcel_repo.create(parcel)
        item_repo.create(TruckTripItem(
            id=uuid4(),
            truck_trip_id=trip.id,
            parcel_id=parcel.id,
            loaded_at=datetime.now(timezone.utc),
        ))

    await depart_trip(
        trip_id=trip.id,
        trip_repo=trip_repo,
        item_repo=item_repo,
        parcel_repo=parcel_repo,
        truck_repo=truck_repo,
        tracking_repo=tracking_repo,
    )

    for parcel in parcels:
        updated = await parcel_repo.get_by_id(parcel.id)
        assert updated.status == ParcelStatus.IN_LINEHAUL_TRANSIT


# Arrive Trip

@pytest.mark.anyio
async def test_arrive_trip_transitions_to_arrived():
    truck_repo = FakeTruckRepo()
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)
    tracking_repo = FakeTrackingRepo()
    trip = make_truck_trip(status=TruckTripStatus.DEPARTED)
    trip_repo.create(trip)

    result = await arrive_trip(
        trip_id=trip.id,
        trip_repo=trip_repo,
        item_repo=item_repo,
        parcel_repo=parcel_repo,
        truck_repo=truck_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == TruckTripStatus.ARRIVED

@pytest.mark.anyio
async def test_arrive_trip_raises_cannot_arrive_when_planned():
    truck_repo = FakeTruckRepo()
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)
    tracking_repo = FakeTrackingRepo()
    trip = make_truck_trip(status=TruckTripStatus.PLANNED)
    trip_repo.create(trip)

    with pytest.raises(TruckTripCannotArrive):
        await arrive_trip(
            trip_id=trip.id,
            trip_repo=trip_repo,
            item_repo=item_repo,
            parcel_repo=parcel_repo,
            truck_repo=truck_repo,
            tracking_repo=tracking_repo,
        )

@pytest.mark.anyio
async def test_arrive_trip_updates_truck_status_to_available():
    truck_repo = FakeTruckRepo()
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    truck = make_truck(status=TruckStatus.IN_TRANSIT)
    truck_repo.create(truck)

    trip = make_truck_trip(status=TruckTripStatus.DEPARTED, truck_id=truck.id)
    trip_repo.create(trip)

    await arrive_trip(
        trip_id=trip.id,
        trip_repo=trip_repo,
        item_repo=item_repo,
        parcel_repo=parcel_repo,
        truck_repo=truck_repo,
        tracking_repo=FakeTrackingRepo(),
    )

    updated_truck = truck_repo.get_by_id(truck.id)
    assert updated_truck.status == TruckStatus.AVAILABLE


# Delete Truck Trip

def test_delete_truck_trip_removes_planned_trip():
    trip_repo = FakeTruckTripRepo()
    trip = make_truck_trip(status=TruckTripStatus.PLANNED)
    trip_repo.create(trip)

    delete_truck_trip(trip.id, trip_repo)

    assert trip_repo.get_by_id(trip.id) is None


def test_delete_truck_trip_raises_not_deletable_when_departed():
    trip_repo = FakeTruckTripRepo()
    trip = make_truck_trip(status=TruckTripStatus.DEPARTED)
    trip_repo.create(trip)

    with pytest.raises(TruckTripNotDeletable):
        delete_truck_trip(trip.id, trip_repo)


# Add Parcel to Trip

@pytest.mark.anyio
async def test_add_parcel_to_trip_succeeds():
    trip_repo = FakeTruckTripRepo()
    truck_repo = FakeTruckRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    truck = make_truck()
    truck_repo.create(truck)

    trip = make_truck_trip(truck_id=truck.id)
    trip_repo.create(trip)

    parcel = make_parcel(
        status=ParcelStatus.AT_ORIGIN_HUB,
        origin_hub_id=trip.origin_hub_id,
        destination_hub_id=trip.destination_hub_id,
    )
    await parcel_repo.create(parcel)

    result = await add_parcel_to_trip(trip.id, parcel.id, trip_repo, item_repo, parcel_repo, truck_repo)

    assert result.parcel_id == parcel.id
    assert result.truck_trip_id == trip.id


@pytest.mark.anyio
async def test_add_parcel_to_trip_raises_parcel_not_found():
    trip_repo = FakeTruckTripRepo()
    truck_repo = FakeTruckRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    trip = make_truck_trip()
    trip_repo.create(trip)

    with pytest.raises(ParcelNotFound):
        await add_parcel_to_trip(trip.id, uuid4(), trip_repo, item_repo, parcel_repo, truck_repo)


@pytest.mark.anyio
async def test_add_parcel_to_trip_raises_invalid_when_parcel_not_at_origin_hub():
    trip_repo = FakeTruckTripRepo()
    truck_repo = FakeTruckRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    trip = make_truck_trip()
    trip_repo.create(trip)

    parcel = make_parcel(
        status=ParcelStatus.AWAITING_PICKUP,
        origin_hub_id=trip.origin_hub_id,
        destination_hub_id=trip.destination_hub_id,
    )
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelForTrip):
        await add_parcel_to_trip(trip.id, parcel.id, trip_repo, item_repo, parcel_repo, truck_repo)


@pytest.mark.anyio
async def test_add_parcel_to_trip_raises_capacity_exceeded():
    trip_repo = FakeTruckTripRepo()
    truck_repo = FakeTruckRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    truck = make_truck(capacity=Capacity(max_weight=0.5, max_volume=0.5))
    truck_repo.create(truck)

    trip = make_truck_trip(truck_id=truck.id)
    trip_repo.create(trip)

    parcel = make_parcel(
        status=ParcelStatus.AT_ORIGIN_HUB,
        origin_hub_id=trip.origin_hub_id,
        destination_hub_id=trip.destination_hub_id,
        load=Load(weight=1.0, volume=1.0),
    )
    await parcel_repo.create(parcel)

    with pytest.raises(CapacityExceeded):
        await add_parcel_to_trip(trip.id, parcel.id, trip_repo, item_repo, parcel_repo, truck_repo)


# Remove Parcel from Trip

def test_remove_parcel_from_trip_succeeds():
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    trip = make_truck_trip(status=TruckTripStatus.PLANNED)
    trip_repo.create(trip)

    item = TruckTripItem(
        id=uuid4(),
        truck_trip_id=trip.id,
        parcel_id=uuid4(),
        loaded_at=datetime.now(timezone.utc),
    )
    item_repo.create(item)

    remove_parcel_from_trip(trip.id, item.id, trip_repo, item_repo)

    assert item_repo.get_by_id(item.id) is None


def test_remove_parcel_from_trip_raises_not_removable_when_departed():
    trip_repo = FakeTruckTripRepo()
    parcel_repo = FakeParcelRepo()
    item_repo = FakeTruckTripItemRepo(parcel_repo)

    trip = make_truck_trip(status=TruckTripStatus.DEPARTED)
    trip_repo.create(trip)

    item = TruckTripItem(
        id=uuid4(),
        truck_trip_id=trip.id,
        parcel_id=uuid4(),
        loaded_at=datetime.now(timezone.utc),
    )
    item_repo.create(item)

    with pytest.raises(TruckTripItemNotRemovable):
        remove_parcel_from_trip(trip.id, item.id, trip_repo, item_repo)