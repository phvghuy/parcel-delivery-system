from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from smart_delivery_routing.application import truck_trip_use_cases
from smart_delivery_routing.application.truck_trip_use_cases import (
    CapacityExceeded, InvalidParcelForTrip, ParcelNotFound,
    TruckTripCannotArrive, TruckTripCannotDepart,
    TruckTripItemNotFound, TruckTripItemNotRemovable,
    TruckTripNotDeletable, TruckTripNotFound, ValidationFailed,
)
from smart_delivery_routing.domain.linehaul import (
    ParcelRepository, TruckRepository, TruckTripItemRepository,
    TruckTripQuery, TruckTripRepository,
)
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from smart_delivery_routing.domain.linehaul.models import TruckTrip, TruckTripItem, TruckTripStatus
from ..dependencies import (
    get_parcel_repo, get_tracking_event_repo, get_truck_repo,
    get_truck_trip_item_repo, get_truck_trip_repo, require_admin,
)
from ..schemas import (
    AddParcelToTripRequest, CreateTruckTripRequest,
    PaginatedTruckTripResponse, TruckTripItemDetailResponse, TruckTripItemResponse, TruckTripResponse,
)

router = APIRouter(prefix="/truck-trips", tags=["truck-trips"])


def _to_response(trip: TruckTrip) -> TruckTripResponse:
    return TruckTripResponse(
        id=str(trip.id),
        truck_id=str(trip.truck_id),
        truck_plate_number=trip.truck_plate_number,
        origin_hub_id=str(trip.origin_hub_id),
        origin_hub_name=trip.origin_hub_name,
        destination_hub_id=str(trip.destination_hub_id),
        destination_hub_name=trip.destination_hub_name,
        status=trip.status.value,
        planned_departure_time=trip.planned_departure_time.isoformat(),
        actual_departure_time=trip.actual_departure_time.isoformat() if trip.actual_departure_time else None,
        actual_arrival_time=trip.actual_arrival_time.isoformat() if trip.actual_arrival_time else None,
        created_at=trip.created_at.isoformat(),
        deleted_at=trip.deleted_at.isoformat() if trip.deleted_at else None,
    )


@router.get("", response_model=PaginatedTruckTripResponse)
def list_truck_trips(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    statuses: list[int] | None = Query(None, description="Lọc theo status: ?statuses=1&statuses=2"),
    include_deleted: bool = Query(False),
    repo: TruckTripRepository = Depends(get_truck_trip_repo),
    _: None = Depends(require_admin),
) -> PaginatedTruckTripResponse:
    query = TruckTripQuery(
        page=page,
        page_size=size,
        statuses=[TruckTripStatus(s) for s in statuses] if statuses else None,
        include_deleted=include_deleted,
    )
    result = truck_trip_use_cases.list_truck_trips(query, repo)
    return PaginatedTruckTripResponse(
        items=[_to_response(t) for t in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{trip_id}", response_model=TruckTripResponse)
def get_truck_trip(
    trip_id: str,
    repo: TruckTripRepository = Depends(get_truck_trip_repo),
    _: None = Depends(require_admin),
) -> TruckTripResponse:
    try:
        trip = truck_trip_use_cases.get_truck_trip(UUID(trip_id), repo)
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(trip)


@router.post("", response_model=TruckTripResponse, status_code=201)
def create_truck_trip(
    body: CreateTruckTripRequest,
    repo: TruckTripRepository = Depends(get_truck_trip_repo),
    _: None = Depends(require_admin),
) -> TruckTripResponse:
    try:
        trip = truck_trip_use_cases.create_truck_trip(
            truck_id=UUID(body.truck_id),
            origin_hub_id=UUID(body.origin_hub_id),
            destination_hub_id=UUID(body.destination_hub_id),
            planned_departure_time=datetime.fromisoformat(body.planned_departure_time),
            repo=repo,
        )
    except ValidationFailed as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_response(trip)


@router.delete("/{trip_id}", status_code=204)
def delete_truck_trip(
    trip_id: str,
    repo: TruckTripRepository = Depends(get_truck_trip_repo),
    _: None = Depends(require_admin),
) -> None:
    try:
        truck_trip_use_cases.delete_truck_trip(UUID(trip_id), repo)
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TruckTripNotDeletable as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{trip_id}/depart", response_model=TruckTripResponse)
async def depart_trip(
    trip_id: str,
    trip_repo: TruckTripRepository = Depends(get_truck_trip_repo),
    item_repo: TruckTripItemRepository = Depends(get_truck_trip_item_repo),
    parcel_repo: ParcelRepository = Depends(get_parcel_repo),
    truck_repo: TruckRepository = Depends(get_truck_repo),
    tracking_repo: TrackingEventRepository = Depends(get_tracking_event_repo),
    _: None = Depends(require_admin),
) -> TruckTripResponse:
    try:
        trip = await truck_trip_use_cases.depart_trip(
            trip_id=UUID(trip_id),
            trip_repo=trip_repo,
            item_repo=item_repo,
            parcel_repo=parcel_repo,
            truck_repo=truck_repo,
            tracking_repo=tracking_repo,
        )
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TruckTripCannotDepart as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _to_response(trip)


@router.post("/{trip_id}/arrive", response_model=TruckTripResponse)
async def arrive_trip(
    trip_id: str,
    trip_repo: TruckTripRepository = Depends(get_truck_trip_repo),
    item_repo: TruckTripItemRepository = Depends(get_truck_trip_item_repo),
    parcel_repo: ParcelRepository = Depends(get_parcel_repo),
    truck_repo: TruckRepository = Depends(get_truck_repo),
    tracking_repo: TrackingEventRepository = Depends(get_tracking_event_repo),
    _: None = Depends(require_admin),
) -> TruckTripResponse:
    try:
        trip = await truck_trip_use_cases.arrive_trip(
            trip_id=UUID(trip_id),
            trip_repo=trip_repo,
            item_repo=item_repo,
            parcel_repo=parcel_repo,
            truck_repo=truck_repo,
            tracking_repo=tracking_repo,
        )
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TruckTripCannotArrive as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _to_response(trip)


def _to_item_response(item: TruckTripItem) -> TruckTripItemResponse:
    return TruckTripItemResponse(
        id=str(item.id),
        truck_trip_id=str(item.truck_trip_id),
        parcel_id=str(item.parcel_id),
        loaded_at=item.loaded_at.isoformat(),
        unloaded_at=item.unloaded_at.isoformat() if item.unloaded_at else None,
    )


@router.get("/{trip_id}/items", response_model=list[TruckTripItemDetailResponse])
def list_trip_items(
    trip_id: str,
    trip_repo: TruckTripRepository = Depends(get_truck_trip_repo),
    item_repo: TruckTripItemRepository = Depends(get_truck_trip_item_repo),
    parcel_repo: ParcelRepository = Depends(get_parcel_repo),
    _: None = Depends(require_admin),
) -> list[TruckTripItemDetailResponse]:
    try:
        truck_trip_use_cases.get_truck_trip(UUID(trip_id), trip_repo)
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    items = item_repo.list_by_trip_id(UUID(trip_id))
    result = []
    for item in items:
        parcel = parcel_repo.get_by_id(item.parcel_id)
        if parcel:
            result.append(TruckTripItemDetailResponse(
                id=str(item.id),
                parcel_id=str(item.parcel_id),
                tracking_number=parcel.tracking_number,
                weight=parcel.load.weight,
                volume=parcel.load.volume,
                parcel_status=parcel.status.value,
                loaded_at=item.loaded_at.isoformat(),
                unloaded_at=item.unloaded_at.isoformat() if item.unloaded_at else None,
            ))
    return result


@router.post("/{trip_id}/items", response_model=TruckTripItemResponse, status_code=201)
async def add_parcel_to_trip(
    trip_id: str,
    body: AddParcelToTripRequest,
    trip_repo: TruckTripRepository = Depends(get_truck_trip_repo),
    item_repo: TruckTripItemRepository = Depends(get_truck_trip_item_repo),
    parcel_repo: ParcelRepository = Depends(get_parcel_repo),
    truck_repo: TruckRepository = Depends(get_truck_repo),
    _: None = Depends(require_admin),
) -> TruckTripItemResponse:
    try:
        item = await truck_trip_use_cases.add_parcel_to_trip(
            trip_id=UUID(trip_id),
            parcel_id=UUID(body.parcel_id),
            trip_repo=trip_repo,
            item_repo=item_repo,
            parcel_repo=parcel_repo,
            truck_repo=truck_repo,
        )
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ParcelNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidParcelForTrip as e:
        raise HTTPException(status_code=422, detail=str(e))
    except CapacityExceeded as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_item_response(item)


@router.delete("/{trip_id}/items/{item_id}", status_code=204)
def remove_parcel_from_trip(
    trip_id: str,
    item_id: str,
    trip_repo: TruckTripRepository = Depends(get_truck_trip_repo),
    item_repo: TruckTripItemRepository = Depends(get_truck_trip_item_repo),
    _: None = Depends(require_admin),
) -> None:
    try:
        truck_trip_use_cases.remove_parcel_from_trip(
            trip_id=UUID(trip_id),
            item_id=UUID(item_id),
            trip_repo=trip_repo,
            item_repo=item_repo,
        )
    except TruckTripNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TruckTripItemNotRemovable as e:
        raise HTTPException(status_code=409, detail=str(e))
    except TruckTripItemNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))