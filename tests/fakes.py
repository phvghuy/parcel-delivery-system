from uuid import UUID

from smart_delivery_routing.domain.linehaul import (
    HubRepository, ParcelRepository, TruckRepository, TruckTripRepository, TruckTripItemRepository,
)
from smart_delivery_routing.domain.linehaul.models import Hub, Parcel, Truck, TruckTrip, TruckTripItem
from smart_delivery_routing.domain.linehaul.queries import HubQuery, ParcelQuery, TruckQuery, TruckTripQuery
from smart_delivery_routing.domain.delivery import DeliveryRouteRepository, DriverRepository, RouteStopRepository
from smart_delivery_routing.domain.delivery.models import DeliveryRoute, DeliveryRouteStatus, Driver, RouteStop
from smart_delivery_routing.domain.delivery.queries import DriverQuery
from smart_delivery_routing.domain.notification import NotificationRepository
from smart_delivery_routing.domain.notification.models import Notification
from smart_delivery_routing.domain.shipping import ShippingRequestRepository
from smart_delivery_routing.domain.shipping.models import ShippingRequest, ShippingRequestStatus
from smart_delivery_routing.domain.shipping.queries import ShippingRequestQuery
from smart_delivery_routing.domain.shared import Load
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from smart_delivery_routing.domain.tracking.models import TrackingEvent
from smart_delivery_routing.application.services import AuthService, AuthToken, JobService, JobStatus


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


class FakeHubRepo(HubRepository):
    def __init__(self):
        self._store: list[Hub] = []

    async def create(self, hub: Hub) -> Hub:
        self._store.append(hub)
        return hub

    async def get_by_id(self, hub_id: UUID) -> Hub | None:
        for h in self._store:
            if h.id == hub_id:
                return h
        return None

    async def update(self, hub: Hub) -> Hub:
        for i, h in enumerate(self._store):
            if h.id == hub.id:
                self._store[i] = hub
                return hub
        return hub

    async def delete(self, hub_id: UUID) -> None:
        self._store = [h for h in self._store if h.id != hub_id]

    async def find_nearest(self, location, limit: int = 1) -> list[Hub]:
        return list(self._store)[:limit]

    async def list(self, query: HubQuery) -> tuple[list[Hub], int]:
        return list(self._store), len(self._store)


class FakeDriverRepo(DriverRepository):
    def __init__(self):
        self._store: list[Driver] = []

    def create(self, driver: Driver) -> Driver:
        self._store.append(driver)
        return driver

    def get_by_id(self, driver_id: UUID) -> Driver | None:
        for d in self._store:
            if d.id == driver_id:
                return d
        return None

    def update(self, driver: Driver) -> Driver:
        for i, d in enumerate(self._store):
            if d.id == driver.id:
                self._store[i] = driver
                return driver
        return driver

    def delete(self, driver_id: UUID) -> None:
        self._store = [d for d in self._store if d.id != driver_id]

    def update_fcm_token(self, driver_id: str, fcm_token: str) -> None:
        for d in self._store:
            if str(d.id) == str(driver_id):
                d.fcm_token = fcm_token

    def list_available(self) -> list[Driver]:
        from smart_delivery_routing.domain.delivery.models import DriverStatus
        return [d for d in self._store if d.status == DriverStatus.AVAILABLE]

    def list(self, query: DriverQuery) -> tuple[list[Driver], int]:
        return list(self._store), len(self._store)


class FakeDeliveryRouteRepo(DeliveryRouteRepository):
    def __init__(self):
        self._store: list[DeliveryRoute] = []

    def save(self, route: DeliveryRoute) -> DeliveryRoute:
        self._store.append(route)
        return route

    def get_by_id(self, route_id: UUID) -> DeliveryRoute | None:
        for r in self._store:
            if r.id == route_id:
                return r
        return None

    def get_by_driver_id(self, driver_id: UUID) -> DeliveryRoute | None:
        for r in self._store:
            if str(r.driver_id) == str(driver_id):
                return r
        return None

    def list_all(self, date: str | None = None, status: DeliveryRouteStatus | None = None) -> list[DeliveryRoute]:
        items = list(self._store)
        if status is not None:
            items = [r for r in items if r.status == status]
        return items

    def update(self, route: DeliveryRoute) -> DeliveryRoute:
        for i, r in enumerate(self._store):
            if r.id == route.id:
                self._store[i] = route
                return route
        return route


class FakeRouteStopRepo(RouteStopRepository):
    def __init__(self):
        self._store: list[RouteStop] = []

    def save(self, stop: RouteStop) -> RouteStop:
        self._store.append(stop)
        return stop

    def list_active_parcel_ids(self) -> list[UUID]:
        return [s.parcel_id for s in self._store]

    def list_by_route_id(self, route_id: UUID) -> list[RouteStop]:
        return [s for s in self._store if s.route_id == route_id]

    def update(self, stop: RouteStop) -> RouteStop:
        for i, s in enumerate(self._store):
            if s.id == stop.id:
                self._store[i] = stop
                return stop
        return stop


class FakeNotificationRepo(NotificationRepository):
    def __init__(self):
        self._store: list[Notification] = []

    def create(self, notification: Notification) -> Notification:
        self._store.append(notification)
        return notification

    def get_by_driver(self, driver_id: str) -> list[Notification]:
        return [n for n in self._store if n.driver_id == driver_id]

    def mark_as_read(self, notification_id: str, driver_id: str) -> None:
        for n in self._store:
            if n.notification_id == notification_id and n.driver_id == driver_id:
                n.is_read = True


class FakeShippingRequestRepo(ShippingRequestRepository):
    def __init__(self):
        self._store: list[ShippingRequest] = []

    def create(self, request: ShippingRequest) -> ShippingRequest:
        self._store.append(request)
        return request

    def get_by_id(self, request_id: UUID) -> ShippingRequest | None:
        for r in self._store:
            if r.id == request_id:
                return r
        return None

    def list(self, query: ShippingRequestQuery) -> list[ShippingRequest]:
        return list(self._store)

    def update_status(self, request_id: UUID, status: ShippingRequestStatus) -> None:
        for r in self._store:
            if r.id == request_id:
                r.status = status


class FakeJobService(JobService):
    def __init__(self):
        self.enqueued_request_ids: list[UUID] = []

    def submit(self, token: str) -> str:
        return "job-1"

    def get_status(self, job_id: str) -> JobStatus:
        return JobStatus(job_id=job_id, status="success")

    def enqueue_process_shipping_request(self, request_id: UUID) -> None:
        self.enqueued_request_ids.append(request_id)


class FakeAuthService(AuthService):
    def __init__(self, valid_email="admin@sdr.com", valid_password="admin"):
        self._valid_email = valid_email
        self._valid_password = valid_password

    def sign_in(self, email: str, password: str) -> AuthToken:
        if email != self._valid_email or password != self._valid_password:
            raise ValueError("Invalid credentials.")
        return AuthToken(access_token="fake-token", role="admin")

    def sign_out(self, token: str) -> None:
        pass