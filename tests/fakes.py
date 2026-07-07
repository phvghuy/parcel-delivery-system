from uuid import UUID

from smart_delivery_routing.domain.linehaul import (
    ParcelRepository, TruckRepository, TruckTripRepository, TruckTripItemRepository,
)
from smart_delivery_routing.domain.linehaul.models import Parcel, Truck, TruckTrip, TruckTripItem
from smart_delivery_routing.domain.linehaul.queries import ParcelQuery, TruckQuery, TruckTripQuery
from smart_delivery_routing.domain.shared import Load
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from smart_delivery_routing.domain.tracking.models import TrackingEvent


class FakeParcelRepo(ParcelRepository):
    def __init__(self):
        self._store: list[Parcel] = []

    async def create(self, parcel: Parcel) -> Parcel:
        self._store.append(parcel)
        return parcel

    async def get_by_id(self, parcel_id: UUID) -> Parcel | None:
        for p in self._store:
            if p.id == parcel_id:
                return p
        return None

    async def list(self, query: ParcelQuery) -> list[Parcel]:
        return list(self._store)

    async def update(self, parcel: Parcel) -> Parcel:
        for i, p in enumerate(self._store):
            if p.id == parcel.id:
                self._store[i] = parcel
                return parcel
        return parcel


class FakeTrackingRepo(TrackingEventRepository):
    def __init__(self):
        self.events: list[TrackingEvent] = []

    def create(self, event: TrackingEvent) -> TrackingEvent:
        self.events.append(event)
        return event

    def list_by_parcel_id(self, parcel_id: UUID) -> list[TrackingEvent]:
        return [e for e in self.events if e.parcel_id == parcel_id]


class FakeTruckRepo(TruckRepository):
    def __init__(self):
        self._store: list[Truck] = []

    def create(self, truck: Truck) -> Truck:
        self._store.append(truck)
        return truck

    def get_by_id(self, truck_id: UUID) -> Truck | None:
        for t in self._store:
            if t.id == truck_id:
                return t
        return None

    def list(self, query: TruckQuery) -> tuple[list[Truck], int]:
        return list(self._store), len(self._store)

    def update(self, truck: Truck) -> Truck:
        for i, t in enumerate(self._store):
            if t.id == truck.id:
                self._store[i] = truck
                return truck
        return truck

    def delete(self, truck_id: UUID) -> None:
        self._store = [t for t in self._store if t.id != truck_id]


class FakeTruckTripRepo(TruckTripRepository):
    def __init__(self):
        self._store: list[TruckTrip] = []

    def create(self, trip: TruckTrip) -> TruckTrip:
        self._store.append(trip)
        return trip

    def get_by_id(self, trip_id: UUID) -> TruckTrip | None:
        for t in self._store:
            if t.id == trip_id:
                return t
        return None

    def list(self, query: TruckTripQuery) -> tuple[list[TruckTrip], int]:
        return list(self._store), len(self._store)

    def update(self, trip: TruckTrip) -> TruckTrip:
        for i, t in enumerate(self._store):
            if t.id == trip.id:
                self._store[i] = trip
                return trip
        return trip

    def delete(self, trip_id: UUID) -> None:
        self._store = [t for t in self._store if t.id != trip_id]


class FakeTruckTripItemRepo(TruckTripItemRepository):
    def __init__(self, parcel_repo: FakeParcelRepo):
        self._store: list[TruckTripItem] = []
        self._parcel_repo = parcel_repo

    def create(self, item: TruckTripItem) -> TruckTripItem:
        self._store.append(item)
        return item

    def get_by_id(self, item_id: UUID) -> TruckTripItem | None:
        for i in self._store:
            if i.id == item_id:
                return i
        return None

    def list_by_trip_id(self, trip_id: UUID) -> list[TruckTripItem]:
        return [i for i in self._store if i.truck_trip_id == trip_id]

    def get_used_load_by_trip_id(self, trip_id: UUID) -> Load:
        items = self.list_by_trip_id(trip_id)
        total_weight = 0.0
        total_volume = 0.0
        for item in items:
            parcel = next((p for p in self._parcel_repo._store if p.id == item.parcel_id), None)
            if parcel is not None:
                total_weight += parcel.load.weight
                total_volume += parcel.load.volume
        return Load(weight=total_weight, volume=total_volume)

    def delete(self, item_id: UUID) -> None:
        self._store = [i for i in self._store if i.id != item_id]