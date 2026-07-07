"""
Unit tests cho shipping_use_cases.
Dùng fake in-memory repositories — không cần Supabase hay bất kỳ service nào.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from smart_delivery_routing.application.services import JobService, JobStatus
from smart_delivery_routing.application.shipping_use_cases import (
    InvalidStatusTransition,
    ShippingRequestNotFound,
    ValidationFailed,
    create_shipping_request,
    process_shipping_request,
    get_shipping_request,
    update_shipping_status,
)
from smart_delivery_routing.domain.linehaul import Hub, HubRepository, HubStatus, HubType, ParcelRepository
from smart_delivery_routing.domain.linehaul.models import Parcel
from smart_delivery_routing.domain.linehaul.queries import HubQuery, ParcelQuery
from smart_delivery_routing.domain.shared import Address, Capacity, Load, Location, Money
from smart_delivery_routing.domain.shipping import (
    ShippingRequest, ShippingRequestRepository, ShippingRequestStatus, ServiceLevel,
)
from smart_delivery_routing.domain.shipping.models import Receiver
from smart_delivery_routing.domain.shipping.queries import ShippingRequestQuery
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from smart_delivery_routing.domain.tracking.models import TrackingEvent


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeShippingRepo(ShippingRequestRepository):
    def __init__(self):
        self._store: dict[UUID, ShippingRequest] = {}

    def create(self, request: ShippingRequest) -> ShippingRequest:
        self._store[request.id] = request
        return request

    def get_by_id(self, request_id: UUID) -> ShippingRequest | None:
        return self._store.get(request_id)

    def list(self, query: ShippingRequestQuery) -> list[ShippingRequest]:
        return list(self._store.values())

    def update_status(self, request_id: UUID, status: ShippingRequestStatus) -> None:
        r = self._store[request_id]
        self._store[request_id] = ShippingRequest(
            id=r.id, external_order_id=r.external_order_id, seller_id=r.seller_id,
            pickup_address=r.pickup_address, delivery_address=r.delivery_address,
            receiver=r.receiver, load=r.load, created_at=r.created_at,
            service_type=r.service_type, cod_amount=r.cod_amount, status=status,
        )


class FakeHubRepo(HubRepository):
    """Trả về danh sách hub được thiết lập sẵn khi gọi find_nearest."""

    def __init__(self, hubs_to_return: list[Hub]):
        self._hubs = hubs_to_return

    async def create(self, hub: Hub) -> Hub: return hub
    async def get_by_id(self, hub_id: UUID) -> Hub | None: return None
    async def list(self, query: HubQuery) -> tuple[list[Hub], int]: return [], 0
    async def update(self, hub: Hub) -> Hub: return hub
    async def delete(self, hub_id: UUID) -> None: pass

    async def find_nearest(self, location: Location, limit: int = 1) -> list[Hub]:
        return self._hubs[:limit]


class FakeParcelRepo(ParcelRepository):
    def __init__(self):
        self.created: list[Parcel] = []

    async def create(self, parcel: Parcel) -> Parcel:
        self.created.append(parcel)
        return parcel

    async def get_by_id(self, parcel_id: UUID) -> Parcel | None: return None
    async def list(self, query: ParcelQuery) -> list[Parcel]: return []
    async def update(self, parcel: Parcel) -> Parcel: return parcel


class FakeTrackingRepo(TrackingEventRepository):
    def create(self, event: TrackingEvent) -> TrackingEvent: return event
    def list_by_parcel_id(self, parcel_id: UUID) -> list[TrackingEvent]: return []


class FakeJobService(JobService):
    def __init__(self):
        self.enqueued: list[UUID] = []

    def submit(self, token: str) -> str: return ""
    def get_status(self, job_id: str) -> JobStatus: return JobStatus(job_id=job_id, status="pending")

    def enqueue_process_shipping_request(self, request_id: UUID) -> None:
        self.enqueued.append(request_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_hub(name: str = "Hub A") -> Hub:
    return Hub(
        id=uuid4(), name=name,
        type=HubType.SORTING_CENTER,
        address=Address(text="123 abc", location=Location(lat=10.78, lng=106.70)),
        status=HubStatus.ACTIVE,
    )


def _make_request(**overrides) -> ShippingRequest:
    defaults = dict(
        id=uuid4(),
        external_order_id="ORD-001",
        seller_id=uuid4(),
        pickup_address=Address(text="123 Nguyen Hue", location=Location(lat=10.78, lng=106.70)),
        delivery_address=Address(text="456 Le Loi", location=Location(lat=10.80, lng=106.72)),
        receiver=Receiver(name="Nguyen Van A", phone="0901234567"),
        load=Load(weight=2.0, volume=0.05),
        created_at=datetime.now(timezone.utc),
        service_type=ServiceLevel.STANDARD,
        cod_amount=None,
        status=ShippingRequestStatus.CREATED,
    )
    return ShippingRequest(**{**defaults, **overrides})


def _make_repos(hubs: list[Hub]):
    return FakeShippingRepo(), FakeHubRepo(hubs), FakeParcelRepo(), FakeTrackingRepo()


# ── create_shipping_request ───────────────────────────────────────────────────

def test_create_saves_with_created_status():
    shipping_repo = FakeShippingRepo()
    job_service = FakeJobService()

    result = create_shipping_request(_make_request(), shipping_repo, job_service)

    assert result.status == ShippingRequestStatus.CREATED


def test_create_enqueues_job():
    shipping_repo = FakeShippingRepo()
    job_service = FakeJobService()
    request = _make_request()

    create_shipping_request(request, shipping_repo, job_service)

    assert request.id in job_service.enqueued


def test_create_raises_validation_failed_on_bad_data():
    shipping_repo = FakeShippingRepo()
    job_service = FakeJobService()

    with pytest.raises(ValidationFailed):
        create_shipping_request(_make_request(external_order_id=""), shipping_repo, job_service)


def test_create_validation_failed_does_not_save():
    shipping_repo = FakeShippingRepo()
    job_service = FakeJobService()

    with pytest.raises(ValidationFailed):
        create_shipping_request(_make_request(external_order_id=""), shipping_repo, job_service)

    assert len(shipping_repo._store) == 0


def test_create_validation_failed_does_not_enqueue():
    shipping_repo = FakeShippingRepo()
    job_service = FakeJobService()

    with pytest.raises(ValidationFailed):
        create_shipping_request(_make_request(external_order_id=""), shipping_repo, job_service)

    assert len(job_service.enqueued) == 0


# ── process_shipping_request ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_process_accepted_when_both_hubs_found():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([_make_hub()])
    request = _make_request()
    shipping_repo.create(request)

    await process_shipping_request(request.id, shipping_repo, hub_repo, parcel_repo, tracking_repo)

    assert shipping_repo.get_by_id(request.id).status == ShippingRequestStatus.ACCEPTED


@pytest.mark.anyio
async def test_process_accepted_creates_parcel():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([_make_hub()])
    request = _make_request()
    shipping_repo.create(request)

    await process_shipping_request(request.id, shipping_repo, hub_repo, parcel_repo, tracking_repo)

    assert len(parcel_repo.created) == 1


@pytest.mark.anyio
async def test_process_parcel_links_to_shipping_request():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([_make_hub()])
    request = _make_request()
    shipping_repo.create(request)

    await process_shipping_request(request.id, shipping_repo, hub_repo, parcel_repo, tracking_repo)

    assert parcel_repo.created[0].shipping_request_id == request.id


@pytest.mark.anyio
async def test_process_rejected_when_no_hubs():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([])
    request = _make_request()
    shipping_repo.create(request)

    await process_shipping_request(request.id, shipping_repo, hub_repo, parcel_repo, tracking_repo)

    assert shipping_repo.get_by_id(request.id).status == ShippingRequestStatus.REJECTED


@pytest.mark.anyio
async def test_process_rejected_does_not_create_parcel():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([])
    request = _make_request()
    shipping_repo.create(request)

    await process_shipping_request(request.id, shipping_repo, hub_repo, parcel_repo, tracking_repo)

    assert len(parcel_repo.created) == 0


@pytest.mark.anyio
async def test_process_raises_not_found():
    shipping_repo, hub_repo, parcel_repo, tracking_repo = _make_repos([_make_hub()])

    with pytest.raises(ShippingRequestNotFound):
        await process_shipping_request(uuid4(), shipping_repo, hub_repo, parcel_repo, tracking_repo)


# ── get_shipping_request ──────────────────────────────────────────────────────

def test_get_returns_existing_request():
    repo = FakeShippingRepo()
    request = _make_request()
    repo.create(request)

    result = get_shipping_request(request.id, repo)

    assert result.id == request.id


def test_get_raises_not_found():
    repo = FakeShippingRepo()

    with pytest.raises(ShippingRequestNotFound):
        get_shipping_request(uuid4(), repo)


# ── update_shipping_status ────────────────────────────────────────────────────

def test_update_status_created_to_accepted():
    repo = FakeShippingRepo()
    request = _make_request()
    repo.create(request)

    update_shipping_status(request.id, ShippingRequestStatus.ACCEPTED, repo)

    assert repo.get_by_id(request.id).status == ShippingRequestStatus.ACCEPTED


def test_update_status_created_to_cancelled():
    repo = FakeShippingRepo()
    request = _make_request()
    repo.create(request)

    update_shipping_status(request.id, ShippingRequestStatus.CANCELLED, repo)

    assert repo.get_by_id(request.id).status == ShippingRequestStatus.CANCELLED


def test_update_status_rejected_to_accepted_is_invalid():
    repo = FakeShippingRepo()
    request = _make_request(status=ShippingRequestStatus.REJECTED)
    repo.create(request)

    with pytest.raises(InvalidStatusTransition):
        update_shipping_status(request.id, ShippingRequestStatus.ACCEPTED, repo)


def test_update_status_not_found_raises():
    repo = FakeShippingRepo()

    with pytest.raises(ShippingRequestNotFound):
        update_shipping_status(uuid4(), ShippingRequestStatus.ACCEPTED, repo)