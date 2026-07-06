from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from smart_delivery_routing.application import hub_use_cases
from smart_delivery_routing.application.hub_use_cases import HubNotFound, ValidationFailed
from smart_delivery_routing.domain.linehaul import Hub, HubQuery, HubRepository, HubStatus, HubType
from smart_delivery_routing.domain.shared import Address, Location
from ..dependencies import get_hub_repo, require_admin
from ..schemas import CreateHubRequest, HubResponse, PaginatedHubResponse, UpdateHubRequest

router = APIRouter(prefix="/hubs", tags=["hubs"])


def _to_response(hub: Hub) -> HubResponse:
    return HubResponse(
        id=str(hub.id),
        name=hub.name,
        type=hub.type.value,
        address_text=hub.address.text,
        lat=hub.address.location.lat,
        lng=hub.address.location.lng,
        status=hub.status.value,
        deleted_at=hub.deleted_at.isoformat() if hub.deleted_at else None,
    )


@router.get("", response_model=PaginatedHubResponse)
async def list_hubs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Tìm theo tên, địa chỉ. Nhiều từ khóa cách nhau bằng dấu phẩy"),
    statuses: list[int] | None = Query(None, description="Lọc theo status: ?statuses=0&statuses=1"),
    types: list[int] | None = Query(None, description="Lọc theo loại hub: ?types=1&types=2"),
    include_deleted: bool = Query(False),
    hub_repo: HubRepository = Depends(get_hub_repo),
    _: None = Depends(require_admin),
) -> PaginatedHubResponse:
    query = HubQuery(
        page=page,
        page_size=size,
        search=search,
        statuses=[HubStatus(s) for s in statuses] if statuses else None,
        types=[HubType(t) for t in types] if types else None,
        include_deleted=include_deleted,
    )
    result = await hub_use_cases.list_hubs(query, hub_repo)
    return PaginatedHubResponse(
        items=[_to_response(h) for h in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{hub_id}", response_model=HubResponse)
async def get_hub(
    hub_id: str,
    hub_repo: HubRepository = Depends(get_hub_repo),
    _: None = Depends(require_admin),
) -> HubResponse:
    try:
        hub = await hub_use_cases.get_hub(UUID(hub_id), hub_repo)
    except HubNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(hub)


@router.post("", response_model=HubResponse, status_code=201)
async def create_hub(
    body: CreateHubRequest,
    hub_repo: HubRepository = Depends(get_hub_repo),
    _: None = Depends(require_admin),
) -> HubResponse:
    hub = Hub(
        id=UUID(body.id),
        name=body.name,
        type=HubType(body.type),
        address=Address(text=body.address_text, location=Location(lat=body.lat, lng=body.lng)),
        status=HubStatus.ACTIVE,
    )
    try:
        created = await hub_use_cases.create_hub(hub, hub_repo)
    except ValidationFailed as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_response(created)


@router.put("/{hub_id}", response_model=HubResponse)
async def update_hub(
    hub_id: str,
    body: UpdateHubRequest,
    hub_repo: HubRepository = Depends(get_hub_repo),
    _: None = Depends(require_admin),
) -> HubResponse:
    uid = UUID(hub_id)
    updated = Hub(
        id=uid,
        name=body.name,
        type=HubType(body.type),
        address=Address(text=body.address_text, location=Location(lat=body.lat, lng=body.lng)),
        status=HubStatus(body.status),
    )
    try:
        result = await hub_use_cases.update_hub(uid, updated, hub_repo)
    except ValidationFailed as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HubNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_response(result)


@router.delete("/{hub_id}", status_code=204)
async def delete_hub(
    hub_id: str,
    hub_repo: HubRepository = Depends(get_hub_repo),
    _: None = Depends(require_admin),
) -> None:
    try:
        await hub_use_cases.delete_hub(UUID(hub_id), hub_repo)
    except HubNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))