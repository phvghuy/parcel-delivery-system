from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from smart_delivery_routing.application import shipping_use_cases
from smart_delivery_routing.application.shipping_use_cases import (
    InvalidStatusTransition,
    ShippingRequestNotFound,
    ValidationFailed,
)
from smart_delivery_routing.domain.shipping import (
    Receiver,
    ServiceLevel,
    ShippingRequest,
    ShippingRequestRepository,
    ShippingRequestStatus,
)
from smart_delivery_routing.domain.linehaul import HubRepository, ParcelRepository
from smart_delivery_routing.domain.shipping.queries import ShippingRequestQuery
from smart_delivery_routing.domain.shared import Address, Load, Location, Money
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from ..dependencies import get_hub_repo, get_parcel_repo, get_shipping_request_repo, get_tracking_event_repo, require_admin
from ..schemas import (
    CreateShippingRequestRequest,
    CursorPagedShippingRequestResponse,
    ShippingRequestResponse,
)

router = APIRouter(prefix="/shipping-requests", tags=["shipping-requests"])


def _to_response(r: ShippingRequest) -> ShippingRequestResponse:
    return ShippingRequestResponse(
        id=str(r.id),
        external_order_id=r.external_order_id,
        seller_id=str(r.seller_id),
        pickup_address_text=r.pickup_address.text,
        pickup_lat=r.pickup_address.location.lat,
        pickup_lng=r.pickup_address.location.lng,
        delivery_address_text=r.delivery_address.text,
        delivery_lat=r.delivery_address.location.lat,
        delivery_lng=r.delivery_address.location.lng,
        receiver_name=r.receiver.name,
        receiver_phone=r.receiver.phone,
        weight=r.load.weight,
        volume=r.load.volume,
        service_type=r.service_type.value,
        status=r.status.value,
        cod_amount=r.cod_amount.amount if r.cod_amount else None,
        cod_currency=r.cod_amount.currency if r.cod_amount else None,
        created_at=r.created_at.isoformat(),
    )


@router.get("", response_model=CursorPagedShippingRequestResponse)
def list_shipping_requests(
    cursor: str | None = Query(None, description="Opaque cursor từ response trước"),
    size: int = Query(20, ge=1, le=100),
    statuses: list[int] | None = Query(None, description="Lọc theo status: ?statuses=1&statuses=2"),
    service_types: list[int] | None = Query(None, description="Lọc theo loại dịch vụ: ?service_types=1"),
    repo: ShippingRequestRepository = Depends(get_shipping_request_repo),
    _: None = Depends(require_admin),
) -> CursorPagedShippingRequestResponse:
    query = ShippingRequestQuery(
        page_size=size,
        statuses=[ShippingRequestStatus(s) for s in statuses] if statuses else None,
        service_types=[ServiceLevel(t) for t in service_types] if service_types else None,
    )
    page = shipping_use_cases.list_shipping_requests(query, repo, cursor=cursor)
    return CursorPagedShippingRequestResponse(
        items=[_to_response(r) for r in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/{request_id}", response_model=ShippingRequestResponse)
def get_shipping_request(
    request_id: str,
    repo: ShippingRequestRepository = Depends(get_shipping_request_repo),
    _: None = Depends(require_admin),
) -> ShippingRequestResponse:
    try:
        r = shipping_use_cases.get_shipping_request(UUID(request_id), repo)
    except ShippingRequestNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(r)


@router.post("", response_model=ShippingRequestResponse, status_code=201)
def create_shipping_request(
    body: CreateShippingRequestRequest,
    shipping_repo: ShippingRequestRepository = Depends(get_shipping_request_repo),
    hub_repo: HubRepository = Depends(get_hub_repo),
    parcel_repo: ParcelRepository = Depends(get_parcel_repo),
    tracking_repo: TrackingEventRepository = Depends(get_tracking_event_repo),
    _: None = Depends(require_admin),
) -> ShippingRequestResponse:
    cod_amount = None
    if body.cod_amount is not None:
        cod_amount = Money(amount=body.cod_amount, currency=body.cod_currency)

    request = ShippingRequest(
        id=UUID(body.id),
        external_order_id=body.external_order_id,
        seller_id=UUID(body.seller_id),
        pickup_address=Address(
            text=body.pickup_address_text,
            location=Location(lat=body.pickup_lat, lng=body.pickup_lng),
        ),
        delivery_address=Address(
            text=body.delivery_address_text,
            location=Location(lat=body.delivery_lat, lng=body.delivery_lng),
        ),
        receiver=Receiver(name=body.receiver_name, phone=body.receiver_phone),
        load=Load(weight=body.weight, volume=body.volume),
        service_type=ServiceLevel(body.service_type),
        cod_amount=cod_amount,
        created_at=datetime.now(timezone.utc),
    )

    try:
        created = shipping_use_cases.create_shipping_request(
            request, shipping_repo, hub_repo, parcel_repo, tracking_repo
        )
    except ValidationFailed as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_response(created)


@router.patch("/{request_id}/status", status_code=204)
def update_shipping_status(
    request_id: str,
    status: int = Query(..., description="Status mới: 1=CREATED 2=ACCEPTED 3=REJECTED 4=CANCELLED"),
    repo: ShippingRequestRepository = Depends(get_shipping_request_repo),
    _: None = Depends(require_admin),
) -> None:
    try:
        shipping_use_cases.update_shipping_status(UUID(request_id), ShippingRequestStatus(status), repo)
    except ShippingRequestNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=422, detail=str(e))