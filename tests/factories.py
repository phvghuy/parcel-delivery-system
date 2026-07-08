from datetime import datetime, timezone
from uuid import uuid4

from smart_delivery_routing.domain.linehaul.models import (
    Hub, HubStatus, HubType, Parcel, ParcelStatus, Truck, TruckStatus, TruckTrip, TruckTripStatus,
)
from smart_delivery_routing.domain.delivery.models import (
    DeliveryRoute, DeliveryRouteStatus, Driver, DriverProfile, DriverStatus, RouteStop, RouteStopStatus,
)
from smart_delivery_routing.domain.shipping.models import (
    Receiver, ServiceLevel, ShippingRequest, ShippingRequestStatus,
)
from smart_delivery_routing.domain.notification.models import Notification
from smart_delivery_routing.domain.shared import Address, Capacity, Load, Location


def make_parcel(**overrides) -> Parcel:
    defaults = dict(
        id=uuid4(),
        shipping_request_id=uuid4(),
        tracking_number=str(uuid4()),
        origin_hub_id=uuid4(),
        destination_hub_id=uuid4(),
        load=Load(weight=1.0, volume=1.0),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        current_hub_id=None,
        status=ParcelStatus.AWAITING_PICKUP,
        origin_hub_name="Hub A",
        destination_hub_name="Hub B",
        current_hub_name="",
    )
    return Parcel(**{**defaults, **overrides})


def make_truck(**overrides) -> Truck:
    defaults = dict(
        id=uuid4(),
        plate_number="51A-123.45",
        capacity=Capacity(max_weight=1000.0, max_volume=10.0),
        status=TruckStatus.AVAILABLE,
    )
    return Truck(**{**defaults, **overrides})


def make_truck_trip(**overrides) -> TruckTrip:
    defaults = dict(
        id=uuid4(),
        truck_id=uuid4(),
        origin_hub_id=uuid4(),
        destination_hub_id=uuid4(),
        status=TruckTripStatus.PLANNED,
        planned_departure_time=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        truck_plate_number="51A-123.45",
        origin_hub_name="Hub A",
        destination_hub_name="Hub B",
    )
    return TruckTrip(**{**defaults, **overrides})


def make_hub(**overrides) -> Hub:
    defaults = dict(
        id=uuid4(),
        name="Hub A",
        type=HubType.SORTING_CENTER,
        address=Address(text="123 Nguyen Hue, Q1", location=Location(lat=10.7769, lng=106.7009)),
        status=HubStatus.ACTIVE,
    )
    return Hub(**{**defaults, **overrides})


def make_driver(**overrides) -> Driver:
    defaults = dict(
        id=uuid4(),
        profile=DriverProfile(name="Nguyen Van A", phone="0901234567", plate_number="59H1-12345"),
        current_hub_id=uuid4(),
        capacity=Capacity(max_weight=100.0, max_volume=1.0),
        status=DriverStatus.AVAILABLE,
        fcm_token="",
        hub_name="Hub A",
    )
    return Driver(**{**defaults, **overrides})


def make_delivery_route(**overrides) -> DeliveryRoute:
    defaults = dict(
        id=uuid4(),
        driver_id=uuid4(),
        hub_id=uuid4(),
        status=DeliveryRouteStatus.PLANNED,
        total_distance_km=0.0,
        created_at=datetime.now(timezone.utc),
        driver_name="Nguyen Van A",
        hub_name="Hub A",
        hub_lat=10.7769,
        hub_lng=106.7009,
    )
    return DeliveryRoute(**{**defaults, **overrides})


def make_route_stop(**overrides) -> RouteStop:
    defaults = dict(
        id=uuid4(),
        route_id=uuid4(),
        parcel_id=uuid4(),
        status=RouteStopStatus.PENDING,
        sequence=1,
        location=Location(lat=10.78, lng=106.70),
        tracking_number=str(uuid4()),
    )
    return RouteStop(**{**defaults, **overrides})


def make_shipping_request(**overrides) -> ShippingRequest:
    defaults = dict(
        id=uuid4(),
        external_order_id="ORD-1000",
        seller_id=uuid4(),
        pickup_address=Address(text="123 Nguyen Hue, Q1", location=Location(lat=10.7769, lng=106.7009)),
        delivery_address=Address(text="456 Le Loi, Q3", location=Location(lat=10.78, lng=106.71)),
        receiver=Receiver(name="Nguyen Van B", phone="0909876543"),
        load=Load(weight=1.0, volume=1.0),
        created_at=datetime.now(timezone.utc),
        service_type=ServiceLevel.STANDARD,
        status=ShippingRequestStatus.CREATED,
    )
    return ShippingRequest(**{**defaults, **overrides})


def make_notification(**overrides) -> Notification:
    defaults = dict(
        driver_id="driver-1",
        title="Route assigned",
        body="You have a new delivery route",
        data={},
        notification_id=str(uuid4()),
        is_read=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return Notification(**{**defaults, **overrides})