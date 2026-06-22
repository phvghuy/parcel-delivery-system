import base64
import json
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from smart_delivery_routing.domain.linehaul import HubRepository, ParcelRepository
from smart_delivery_routing.domain.shared import ValidationError
from smart_delivery_routing.domain.shipping import (
    ShippingRequest,
    ShippingRequestQuery,
    ShippingRequestRepository,
    ShippingRequestStatus,
    validate_shipping_request,
)
from smart_delivery_routing.domain.tracking import TrackingEventRepository


@dataclass(frozen=True)
class ValidationFailed(Exception):
    errors: list[ValidationError]

    def __str__(self) -> str:
        return "; ".join(f"{e.field}: {e.reason}" for e in self.errors)


@dataclass(frozen=True)
class ShippingRequestNotFound(Exception):
    request_id: UUID

    def __str__(self) -> str:
        return f"ShippingRequest '{self.request_id}' not found."


@dataclass(frozen=True)
class InvalidStatusTransition(Exception):
    request_id: UUID
    from_status: ShippingRequestStatus
    to_status: ShippingRequestStatus

    def __str__(self) -> str:
        return (
            f"Cannot transition ShippingRequest '{self.request_id}' "
            f"from '{self.from_status.name}' to '{self.to_status.name}'."
        )


# Các chuyển trạng thái hợp lệ
_ALLOWED_TRANSITIONS: dict[ShippingRequestStatus, set[ShippingRequestStatus]] = {
    ShippingRequestStatus.CREATED:   {ShippingRequestStatus.ACCEPTED, ShippingRequestStatus.REJECTED, ShippingRequestStatus.CANCELLED},
    ShippingRequestStatus.ACCEPTED:  {ShippingRequestStatus.REJECTED, ShippingRequestStatus.CANCELLED},
    ShippingRequestStatus.REJECTED:  set(),
    ShippingRequestStatus.CANCELLED: set(),
}


@dataclass(frozen=True)
class ShippingRequestPage:
    items: list[ShippingRequest]
    next_cursor: str | None  # None = last page


def _encode_cursor(item: ShippingRequest) -> str:
    payload = {"created_at": item.created_at.isoformat(), "id": str(item.id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple:
    from datetime import datetime
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])


def list_shipping_requests(
    query: ShippingRequestQuery,
    repo: ShippingRequestRepository,
    cursor: str | None = None,
) -> ShippingRequestPage:
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        query = ShippingRequestQuery(
            page_size=query.page_size,
            statuses=query.statuses,
            service_types=query.service_types,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
    rows = repo.list(query)
    has_next = len(rows) > query.page_size
    items = rows[:query.page_size]
    next_cursor = _encode_cursor(items[-1]) if has_next and items else None
    return ShippingRequestPage(items=items, next_cursor=next_cursor)


def create_shipping_request(
    request: ShippingRequest,
    shipping_repo: ShippingRequestRepository,
    hub_repo: HubRepository,
    parcel_repo: ParcelRepository,
    tracking_repo: TrackingEventRepository,
) -> ShippingRequest:
    from smart_delivery_routing.application.parcel_use_cases import create_parcel

    errors = validate_shipping_request(request)
    if errors:
        raise ValidationFailed(errors=errors)

    saved = shipping_repo.create(request)

    origin_hubs = hub_repo.find_nearest(request.pickup_address.location)
    dest_hubs = hub_repo.find_nearest(request.delivery_address.location)
    origin_hub = origin_hubs[0] if origin_hubs else None
    dest_hub = dest_hubs[0] if dest_hubs else None

    if origin_hub and dest_hub:
        create_parcel(
            parcel_id=uuid4(),
            shipping_request_id=saved.id,
            origin_hub_id=origin_hub.id,
            destination_hub_id=dest_hub.id,
            origin_hub_name=origin_hub.name,
            destination_hub_name=dest_hub.name,
            weight=request.load.weight,
            volume=request.load.volume,
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )
        new_status = ShippingRequestStatus.ACCEPTED
    else:
        new_status = ShippingRequestStatus.REJECTED

    shipping_repo.update_status(saved.id, new_status)
    return replace(saved, status=new_status)


def get_shipping_request(request_id: UUID, repo: ShippingRequestRepository) -> ShippingRequest:
    request = repo.get_by_id(request_id)
    if request is None:
        raise ShippingRequestNotFound(request_id=request_id)
    return request


def update_shipping_status(
    request_id: UUID,
    new_status: ShippingRequestStatus,
    repo: ShippingRequestRepository,
) -> None:
    request = repo.get_by_id(request_id)
    if request is None:
        raise ShippingRequestNotFound(request_id=request_id)
    if new_status not in _ALLOWED_TRANSITIONS[request.status]:
        raise InvalidStatusTransition(
            request_id=request_id,
            from_status=request.status,
            to_status=new_status,
        )
    repo.update_status(request_id, new_status)
