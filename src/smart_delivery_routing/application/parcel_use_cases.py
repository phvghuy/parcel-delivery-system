import base64
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4
from opentelemetry import trace

from smart_delivery_routing.domain.linehaul import Parcel, ParcelQuery, ParcelRepository, ParcelStatus
from smart_delivery_routing.domain.shared import Load
from smart_delivery_routing.domain.tracking import (
    TrackingEvent, TrackingEventRepository, TrackingLocation, TrackingLocationType,
)


tracer = trace.get_tracer(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

@dataclass
class ParcelNotFound(Exception):
    parcel_id: UUID

    def __str__(self) -> str:
        return f"Parcel '{self.parcel_id}' not found."


@dataclass
class InvalidParcelStatusTransition(Exception):
    parcel_id: UUID
    from_status: ParcelStatus
    to_status: ParcelStatus

    def __str__(self) -> str:
        return (
            f"Cannot transition Parcel '{self.parcel_id}' "
            f"from '{self.from_status.name}' to '{self.to_status.name}'."
        )


# ── State machine ─────────────────────────────────────────────────────────────

_ALLOWED_TRANSITIONS: dict[ParcelStatus, set[ParcelStatus]] = {
    ParcelStatus.AWAITING_PICKUP:     {ParcelStatus.PICKED_UP, ParcelStatus.CANCELLED},
    ParcelStatus.PICKED_UP:           {ParcelStatus.AT_ORIGIN_HUB, ParcelStatus.CANCELLED},
    ParcelStatus.AT_ORIGIN_HUB:       {ParcelStatus.IN_LINEHAUL_TRANSIT, ParcelStatus.CANCELLED},
    ParcelStatus.IN_LINEHAUL_TRANSIT: {ParcelStatus.AT_DESTINATION_HUB},
    ParcelStatus.AT_DESTINATION_HUB:  {ParcelStatus.OUT_FOR_DELIVERY, ParcelStatus.CANCELLED},
    ParcelStatus.OUT_FOR_DELIVERY:    {ParcelStatus.DELIVERED, ParcelStatus.DELIVERY_FAILED},
    ParcelStatus.DELIVERY_FAILED:     {ParcelStatus.OUT_FOR_DELIVERY, ParcelStatus.RETURNED},
    ParcelStatus.RETURNED:            set(),
    ParcelStatus.DELIVERED:           set(),
    ParcelStatus.CANCELLED:           set(),
}


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParcelPage:
    items: list[Parcel]
    next_cursor: str | None


# ── Cursor helpers ────────────────────────────────────────────────────────────

def _encode_cursor(item: Parcel) -> str:
    payload = {"created_at": item.created_at.isoformat(), "id": str(item.id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_or_raise(parcel_id: UUID, repo: ParcelRepository) -> Parcel:
    parcel = await repo.get_by_id(parcel_id)
    if parcel is None:
        raise ParcelNotFound(parcel_id=parcel_id)
    return parcel


async def _transition(
    parcel: Parcel,
    new_status: ParcelStatus,
    new_current_hub_id: UUID | None,
    new_current_hub_name: str,
    location: TrackingLocation,
    note: str | None,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    with tracer.start_as_current_span("parcel/transition"):
        span = trace.get_current_span()
        span.set_attribute("parcel.id", str(parcel.id))
        span.set_attribute("parcel.from_status", parcel.status.value)
        span.set_attribute("parcel.to_status", new_status.value)

        if new_status not in _ALLOWED_TRANSITIONS[parcel.status]:
            raise InvalidParcelStatusTransition(
                parcel_id=parcel.id,
                from_status=parcel.status,
                to_status=new_status,
            )
        now = datetime.now(timezone.utc)
        updated = replace(
            parcel,
            status=new_status,
            current_hub_id=new_current_hub_id,
            current_hub_name=new_current_hub_name,
            updated_at=now,
        )
        await parcel_repo.update(updated)
        tracking_repo.create(TrackingEvent(
            id=uuid4(),
            parcel_id=parcel.id,
            status=new_status,
            location=location,
            note=note,
            created_at=now,
        ))
    return updated


# ── Read use cases ────────────────────────────────────────────────────────────

async def get_parcel(parcel_id: UUID, repo: ParcelRepository) -> Parcel:
    return await _get_or_raise(parcel_id, repo)


async def list_parcels(
    query: ParcelQuery,
    repo: ParcelRepository,
    cursor: str | None = None,
) -> ParcelPage:
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        query = ParcelQuery(
            page_size=query.page_size,
            statuses=query.statuses,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
    with tracer.start_as_current_span("parcel/list"):
        rows = await repo.list(query)
    has_next = len(rows) > query.page_size
    items = rows[:query.page_size]
    next_cursor = _encode_cursor(items[-1]) if has_next and items else None
    return ParcelPage(items=items, next_cursor=next_cursor)


# ── Write use cases ───────────────────────────────────────────────────────────

async def create_parcel(
    parcel_id: UUID,
    shipping_request_id: UUID,
    origin_hub_id: UUID,
    destination_hub_id: UUID,
    origin_hub_name: str,
    destination_hub_name: str,
    weight: float,
    volume: float,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    event_id = uuid4()
    now = datetime.now(timezone.utc)

    parcel = Parcel(
        id=parcel_id,
        shipping_request_id=shipping_request_id,
        tracking_number=str(event_id),
        origin_hub_id=origin_hub_id,
        destination_hub_id=destination_hub_id,
        load=Load(weight=weight, volume=volume),
        created_at=now,
        updated_at=now,
        current_hub_id=None,
        status=ParcelStatus.AWAITING_PICKUP,
        origin_hub_name=origin_hub_name,
        destination_hub_name=destination_hub_name,
        current_hub_name="",
    )
    await parcel_repo.create(parcel)
    tracking_repo.create(TrackingEvent(
        id=event_id,
        parcel_id=parcel_id,
        status=ParcelStatus.AWAITING_PICKUP,
        location=TrackingLocation(kind=TrackingLocationType.SYSTEM, name="System"),
        note=None,
        created_at=now,
    ))
    return parcel


# ── Business use cases ────────────────────────────────────────────────────────

async def pickup_parcel(
    parcel_id: UUID,
    driver_id: UUID,
    driver_name: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Tài xế đã đến chỗ người bán và lấy hàng."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.PICKED_UP,
        new_current_hub_id=None,
        new_current_hub_name="",
        location=TrackingLocation(kind=TrackingLocationType.DRIVER, name=driver_name, id=driver_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def deliver_to_origin_hub(
    parcel_id: UUID,
    hub_id: UUID,
    hub_name: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Tài xế đã mang hàng đến sorting center đầu tiên."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.AT_ORIGIN_HUB,
        new_current_hub_id=hub_id,
        new_current_hub_name=hub_name,
        location=TrackingLocation(kind=TrackingLocationType.HUB, name=hub_name, id=hub_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def dispatch_linehaul(
    parcel_id: UUID,
    truck_trip_id: UUID,
    truck_plate: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Hàng được xếp lên xe tải linehaul để vận chuyển liên hub."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.IN_LINEHAUL_TRANSIT,
        new_current_hub_id=None,
        new_current_hub_name="",
        location=TrackingLocation(kind=TrackingLocationType.TRUCK_TRIP, name=truck_plate, id=truck_trip_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def arrive_at_destination_hub(
    parcel_id: UUID,
    hub_id: UUID,
    hub_name: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Xe tải đã đến hub đích, hàng được dỡ xuống."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.AT_DESTINATION_HUB,
        new_current_hub_id=hub_id,
        new_current_hub_name=hub_name,
        location=TrackingLocation(kind=TrackingLocationType.HUB, name=hub_name, id=hub_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def dispatch_for_delivery(
    parcel_id: UUID,
    driver_id: UUID,
    driver_name: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Tài xế lấy hàng từ hub đích để đi giao cho người nhận."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.OUT_FOR_DELIVERY,
        new_current_hub_id=parcel.current_hub_id,
        new_current_hub_name=parcel.current_hub_name,
        location=TrackingLocation(kind=TrackingLocationType.DRIVER, name=driver_name, id=driver_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def confirm_delivery(
    parcel_id: UUID,
    receiver_name: str,
    note: str | None,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Giao hàng thành công, người nhận đã ký nhận."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.DELIVERED,
        new_current_hub_id=None,
        new_current_hub_name="",
        location=TrackingLocation(kind=TrackingLocationType.CUSTOMER, name=receiver_name),
        note=note,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def fail_delivery(
    parcel_id: UUID,
    reason: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Giao hàng thất bại (vắng nhà, sai địa chỉ, từ chối nhận...)."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.DELIVERY_FAILED,
        new_current_hub_id=parcel.current_hub_id,
        new_current_hub_name=parcel.current_hub_name,
        location=TrackingLocation(kind=TrackingLocationType.CUSTOMER, name="Địa chỉ giao hàng"),
        note=reason,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def return_parcel(
    parcel_id: UUID,
    hub_id: UUID,
    hub_name: str,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Hàng được hoàn về hub (sau khi giao thất bại)."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.RETURNED,
        new_current_hub_id=hub_id,
        new_current_hub_name=hub_name,
        location=TrackingLocation(kind=TrackingLocationType.HUB, name=hub_name, id=hub_id),
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )


async def cancel_parcel(
    parcel_id: UUID,
    reason: str | None,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> Parcel:
    """Hủy đơn hàng."""
    parcel = await _get_or_raise(parcel_id, parcel_repo)
    return await _transition(
        parcel,
        new_status=ParcelStatus.CANCELLED,
        new_current_hub_id=None,
        new_current_hub_name="",
        location=TrackingLocation(kind=TrackingLocationType.SYSTEM, name="System"),
        note=reason,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )
