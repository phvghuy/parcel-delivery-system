import pytest
from fastapi.testclient import TestClient

from smart_delivery_routing.interface.api import app
from smart_delivery_routing.interface.api import dependencies as deps

from tests.fakes import (
    FakeAuthService,
    FakeDeliveryRouteRepo,
    FakeDriverRepo,
    FakeHubRepo,
    FakeJobService,
    FakeNotificationRepo,
    FakeParcelRepo,
    FakeRouteStopRepo,
    FakeShippingRequestRepo,
    FakeTrackingRepo,
    FakeTruckRepo,
    FakeTruckTripItemRepo,
    FakeTruckTripRepo,
)

DEFAULT_DRIVER_ID = "11111111-1111-1111-1111-111111111111"


class Fakes:
    def __init__(self):
        self.parcel_repo = FakeParcelRepo()
        self.tracking_repo = FakeTrackingRepo()
        self.truck_repo = FakeTruckRepo()
        self.truck_trip_repo = FakeTruckTripRepo()
        self.truck_trip_item_repo = FakeTruckTripItemRepo(self.parcel_repo)
        self.hub_repo = FakeHubRepo()
        self.driver_repo = FakeDriverRepo()
        self.delivery_route_repo = FakeDeliveryRouteRepo()
        self.route_stop_repo = FakeRouteStopRepo()
        self.notification_repo = FakeNotificationRepo()
        self.shipping_request_repo = FakeShippingRequestRepo()
        self.job_service = FakeJobService()
        self.auth_service = FakeAuthService()


@pytest.fixture
def fakes() -> Fakes:
    return Fakes()


@pytest.fixture
def client(fakes: Fakes):
    app.dependency_overrides[deps.require_admin] = lambda: None
    app.dependency_overrides[deps.require_driver] = lambda: None
    app.dependency_overrides[deps.get_current_driver_id] = lambda: DEFAULT_DRIVER_ID
    app.dependency_overrides[deps.get_parcel_repo] = lambda: fakes.parcel_repo
    app.dependency_overrides[deps.get_readonly_parcel_repo] = lambda: fakes.parcel_repo
    app.dependency_overrides[deps.get_tracking_event_repo] = lambda: fakes.tracking_repo
    app.dependency_overrides[deps.get_truck_repo] = lambda: fakes.truck_repo
    app.dependency_overrides[deps.get_truck_trip_repo] = lambda: fakes.truck_trip_repo
    app.dependency_overrides[deps.get_truck_trip_item_repo] = lambda: fakes.truck_trip_item_repo
    app.dependency_overrides[deps.get_hub_repo] = lambda: fakes.hub_repo
    app.dependency_overrides[deps.get_readonly_hub_repo] = lambda: fakes.hub_repo
    app.dependency_overrides[deps.get_driver_repo] = lambda: fakes.driver_repo
    app.dependency_overrides[deps.get_delivery_route_repo] = lambda: fakes.delivery_route_repo
    app.dependency_overrides[deps.get_route_stop_repo] = lambda: fakes.route_stop_repo
    app.dependency_overrides[deps.get_notification_repo] = lambda: fakes.notification_repo
    app.dependency_overrides[deps.get_shipping_request_repo] = lambda: fakes.shipping_request_repo
    app.dependency_overrides[deps.get_job_service] = lambda: fakes.job_service
    app.dependency_overrides[deps.get_auth_service] = lambda: fakes.auth_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": "Bearer test-token"}
