from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from .models import Hub, Parcel, Truck, TruckTrip, TruckTripItem
from .queries import HubQuery, ParcelQuery, TruckQuery, TruckTripQuery
from ..shared import Load, Location


class ParcelRepository(ABC):
    @abstractmethod
    async def create(self, parcel: Parcel) -> Parcel: ...

    @abstractmethod
    async def get_by_id(self, parcel_id: UUID) -> Parcel | None: ...

    @abstractmethod
    async def list(self, query: ParcelQuery) -> list[Parcel]: ...

    @abstractmethod
    async def update(self, parcel: Parcel) -> Parcel: ...


class HubRepository(ABC):
    @abstractmethod
    async def create(self, hub: Hub) -> Hub: ...

    @abstractmethod
    async def get_by_id(self, hub_id: UUID) -> Hub | None: ...

    @abstractmethod
    async def list(self, query: HubQuery) -> tuple[list[Hub], int]: ...

    @abstractmethod
    async def update(self, hub: Hub) -> Hub: ...

    @abstractmethod
    async def delete(self, hub_id: UUID) -> None: ...

    @abstractmethod
    async def find_nearest(self, location: Location, limit: int = 1) -> list[Hub]: ...


class TruckRepository(ABC):
    @abstractmethod
    def create(self, truck: Truck) -> Truck: ...

    @abstractmethod
    def get_by_id(self, truck_id: UUID) -> Truck | None: ...

    @abstractmethod
    def list(self, query: TruckQuery) -> tuple[list[Truck], int]: ...

    @abstractmethod
    def update(self, truck: Truck) -> Truck: ...

    @abstractmethod
    def delete(self, truck_id: UUID) -> None: ...


class TruckTripRepository(ABC):
    @abstractmethod
    def create(self, trip: TruckTrip) -> TruckTrip: ...

    @abstractmethod
    def get_by_id(self, trip_id: UUID) -> TruckTrip | None: ...

    @abstractmethod
    def list(self, query: TruckTripQuery) -> tuple[list[TruckTrip], int]: ...

    @abstractmethod
    def update(self, trip: TruckTrip) -> TruckTrip: ...

    @abstractmethod
    def delete(self, trip_id: UUID) -> None: ...


class TruckTripItemRepository(ABC):
    @abstractmethod
    def create(self, item: TruckTripItem) -> TruckTripItem: ...

    @abstractmethod
    def get_by_id(self, item_id: UUID) -> TruckTripItem | None: ...

    @abstractmethod
    def list_by_trip_id(self, trip_id: UUID) -> list[TruckTripItem]: ...

    @abstractmethod
    def get_used_load_by_trip_id(self, trip_id: UUID) -> Load: ...

    @abstractmethod
    def delete(self, item_id: UUID) -> None: ...

