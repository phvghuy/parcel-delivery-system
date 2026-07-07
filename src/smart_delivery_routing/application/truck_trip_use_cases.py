from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4
from opentelemetry import trace

from smart_delivery_routing.application.parcel_use_cases import arrive_at_destination_hub, dispatch_linehaul
from smart_delivery_routing.domain.linehaul import (
    ParcelRepository, TruckRepository, TruckTripItemRepository,
    TruckTripQuery, TruckTripRepository, validate_truck_trip,
)
from smart_delivery_routing.domain.linehaul.models import (
    Parcel, ParcelStatus, Truck, TruckStatus, TruckTrip, TruckTripItem, TruckTripStatus,
)
from smart_delivery_routing.domain.shared import ValidationError
from smart_delivery_routing.domain.tracking import TrackingEventRepository


tracer = trace.get_tracer(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

@dataclass
class TruckTripNotFound(Exception):
    trip_id: UUID

    def __str__(self) -> str:
        return f"TruckTrip '{self.trip_id}' not found."


@dataclass
class ValidationFailed(Exception):
    errors: list[ValidationError]

    def __str__(self) -> str:
        return "; ".join(f"{e.field}: {e.reason}" for e in self.errors)


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PagedTruckTrips:
    items: list[TruckTrip]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.size))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_raise(trip_id: UUID, repo: TruckTripRepository) -> TruckTrip:
    trip = repo.get_by_id(trip_id)
    if trip is None:
        raise TruckTripNotFound(trip_id=trip_id)
    return trip


# ── Use cases ─────────────────────────────────────────────────────────────────

def create_truck_trip(
    truck_id: UUID,
    origin_hub_id: UUID,
    destination_hub_id: UUID,
    planned_departure_time: datetime,
    repo: TruckTripRepository,
) -> TruckTrip:
    trip = TruckTrip(
        id=uuid4(),
        truck_id=truck_id,
        origin_hub_id=origin_hub_id,
        destination_hub_id=destination_hub_id,
        status=TruckTripStatus.PLANNED,
        planned_departure_time=planned_departure_time,
        created_at=datetime.now(timezone.utc),
    )
    errors = validate_truck_trip(trip)
    if errors:
        raise ValidationFailed(errors=errors)
    return repo.create(trip)


def get_truck_trip(trip_id: UUID, repo: TruckTripRepository) -> TruckTrip:
    return _get_or_raise(trip_id, repo)


def list_truck_trips(query: TruckTripQuery, repo: TruckTripRepository) -> PagedTruckTrips:
    items, total = repo.list(query)
    return PagedTruckTrips(items=items, total=total, page=query.page, size=query.page_size)


@dataclass
class TruckTripNotDeletable(Exception):
    trip_id: UUID
    status: TruckTripStatus

    def __str__(self) -> str:
        return f"TruckTrip '{self.trip_id}' cannot be deleted in status '{self.status.name}'."


@dataclass
class TruckTripCannotDepart(Exception):
    trip_id: UUID
    status: TruckTripStatus

    def __str__(self) -> str:
        return (
            f"TruckTrip '{self.trip_id}' cannot depart in status '{self.status.name}'. "
            "Must be PLANNED."
        )


async def depart_trip(
    trip_id: UUID,
    trip_repo: TruckTripRepository,
    item_repo: TruckTripItemRepository,
    parcel_repo: ParcelRepository,
    truck_repo: TruckRepository,
    tracking_repo: TrackingEventRepository,
) -> TruckTrip:
    with tracer.start_as_current_span("truck_trip/depart"):
        trip = _get_or_raise(trip_id, trip_repo)

        span = trace.get_current_span()
        span.set_attribute("trip.id", str(trip.id))
        span.set_attribute("trip.truck_id", str(trip.truck_id))

        if trip.status != TruckTripStatus.PLANNED:
            raise TruckTripCannotDepart(trip_id=trip_id, status=trip.status)

        now = datetime.now(timezone.utc)

        updated_trip = replace(trip, status=TruckTripStatus.DEPARTED, actual_departure_time=now)
        trip_repo.update(updated_trip)

        truck: Truck | None = truck_repo.get_by_id(trip.truck_id)
        if truck is not None:
            truck_repo.update(replace(truck, status=TruckStatus.IN_TRANSIT))

        items = item_repo.list_by_trip_id(trip_id)

        span.set_attribute("parcel_count", len(items))

        for item in items:
            try:
                await dispatch_linehaul(
                    parcel_id=item.parcel_id,
                    truck_trip_id=trip_id,
                    truck_plate=trip.truck_plate_number,
                    parcel_repo=parcel_repo,
                    tracking_repo=tracking_repo,
                )
            except Exception:
                pass  # best-effort: không để 1 parcel lỗi block toàn bộ chuyến

    return updated_trip


@dataclass
class TruckTripCannotArrive(Exception):
    trip_id: UUID
    status: TruckTripStatus

    def __str__(self) -> str:
        return (
            f"TruckTrip '{self.trip_id}' cannot arrive in status '{self.status.name}'. "
            "Must be DEPARTED."
        )


async def arrive_trip(
    trip_id: UUID,
    trip_repo: TruckTripRepository,
    item_repo: TruckTripItemRepository,
    parcel_repo: ParcelRepository,
    truck_repo: TruckRepository,
    tracking_repo: TrackingEventRepository,
) -> TruckTrip:
    with tracer.start_as_current_span("truck_trip/arrive"):
        trip = _get_or_raise(trip_id, trip_repo)

        span = trace.get_current_span()
        span.set_attribute("trip.id", str(trip.id))
        span.set_attribute("trip.destination_hub_id", str(trip.destination_hub_id))

        if trip.status != TruckTripStatus.DEPARTED:
            raise TruckTripCannotArrive(trip_id=trip_id, status=trip.status)

        now = datetime.now(timezone.utc)

        updated_trip = replace(trip, status=TruckTripStatus.ARRIVED, actual_arrival_time=now)
        trip_repo.update(updated_trip)

        truck: Truck | None = truck_repo.get_by_id(trip.truck_id)
        if truck is not None:
            truck_repo.update(replace(truck, status=TruckStatus.AVAILABLE))

        items = item_repo.list_by_trip_id(trip_id)

        span.set_attribute("parcel_count", len(items))

        for item in items:
            try:
                await arrive_at_destination_hub(
                    parcel_id=item.parcel_id,
                    hub_id=trip.destination_hub_id,
                    hub_name=trip.destination_hub_name,
                    parcel_repo=parcel_repo,
                    tracking_repo=tracking_repo,
                )
            except Exception:
                pass  # best-effort

    return updated_trip


def delete_truck_trip(trip_id: UUID, repo: TruckTripRepository) -> None:
    trip = _get_or_raise(trip_id, repo)
    if trip.status != TruckTripStatus.PLANNED:
        raise TruckTripNotDeletable(trip_id=trip_id, status=trip.status)
    repo.delete(trip_id)


# ── TruckTripItem exceptions ──────────────────────────────────────────────────

@dataclass
class TruckTripItemNotFound(Exception):
    item_id: UUID

    def __str__(self) -> str:
        return f"TruckTripItem '{self.item_id}' not found."


@dataclass
class ParcelNotFound(Exception):
    parcel_id: UUID

    def __str__(self) -> str:
        return f"Parcel '{self.parcel_id}' not found."


@dataclass
class InvalidParcelForTrip(Exception):
    parcel_id: UUID
    reason: str

    def __str__(self) -> str:
        return f"Parcel '{self.parcel_id}' cannot be added to trip: {self.reason}."


@dataclass
class CapacityExceeded(Exception):
    trip_id: UUID
    required_weight: float
    required_volume: float
    available_weight: float
    available_volume: float

    def __str__(self) -> str:
        parts = []
        if self.required_weight > self.available_weight:
            parts.append(f"weight (required {self.required_weight}, available {self.available_weight:.2f})")
        if self.required_volume > self.available_volume:
            parts.append(f"volume (required {self.required_volume}, available {self.available_volume:.2f})")
        return f"TruckTrip '{self.trip_id}' capacity exceeded: {', '.join(parts)}."


@dataclass
class TruckTripItemNotRemovable(Exception):
    trip_id: UUID
    trip_status: TruckTripStatus

    def __str__(self) -> str:
        return (
            f"Cannot remove parcel from TruckTrip '{self.trip_id}' "
            f"in status '{self.trip_status.name}'. Trip must be PLANNED."
        )


# ── TruckTripItem use cases ───────────────────────────────────────────────────

async def add_parcel_to_trip(
    trip_id: UUID,
    parcel_id: UUID,
    trip_repo: TruckTripRepository,
    item_repo: TruckTripItemRepository,
    parcel_repo: ParcelRepository,
    truck_repo: TruckRepository,
) -> TruckTripItem:
    trip = _get_or_raise(trip_id, trip_repo)

    parcel: Parcel | None = await parcel_repo.get_by_id(parcel_id)
    if parcel is None:
        raise ParcelNotFound(parcel_id=parcel_id)

    if parcel.status != ParcelStatus.AT_ORIGIN_HUB:
        raise InvalidParcelForTrip(
            parcel_id=parcel_id,
            reason=f"parcel status must be AT_ORIGIN_HUB, got {parcel.status.name}",
        )
    if parcel.origin_hub_id != trip.origin_hub_id:
        raise InvalidParcelForTrip(
            parcel_id=parcel_id,
            reason="parcel origin hub does not match trip origin hub",
        )
    if parcel.destination_hub_id != trip.destination_hub_id:
        raise InvalidParcelForTrip(
            parcel_id=parcel_id,
            reason="parcel destination hub does not match trip destination hub",
        )

    truck = truck_repo.get_by_id(trip.truck_id)
    used = item_repo.get_used_load_by_trip_id(trip_id)
    available_weight = truck.capacity.max_weight - used.weight
    available_volume = truck.capacity.max_volume - used.volume

    if parcel.load.weight > available_weight or parcel.load.volume > available_volume:
        raise CapacityExceeded(
            trip_id=trip_id,
            required_weight=parcel.load.weight,
            required_volume=parcel.load.volume,
            available_weight=available_weight,
            available_volume=available_volume,
        )

    item = TruckTripItem(
        id=uuid4(),
        truck_trip_id=trip_id,
        parcel_id=parcel_id,
        loaded_at=datetime.now(timezone.utc),
    )
    return item_repo.create(item)


def remove_parcel_from_trip(
    trip_id: UUID,
    item_id: UUID,
    trip_repo: TruckTripRepository,
    item_repo: TruckTripItemRepository,
) -> None:
    trip = _get_or_raise(trip_id, trip_repo)
    if trip.status != TruckTripStatus.PLANNED:
        raise TruckTripItemNotRemovable(trip_id=trip_id, trip_status=trip.status)

    item = item_repo.get_by_id(item_id)
    if item is None:
        raise TruckTripItemNotFound(item_id=item_id)

    item_repo.delete(item_id)