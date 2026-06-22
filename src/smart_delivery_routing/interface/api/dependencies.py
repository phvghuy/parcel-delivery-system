from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from supabase import Client

from smart_delivery_routing.application.services import AuthService, NotificationService
from smart_delivery_routing.domain.delivery import DeliveryRouteRepository, DriverRepository, RouteStopRepository
from smart_delivery_routing.domain.linehaul import HubRepository, ParcelRepository, TruckRepository, TruckTripItemRepository, TruckTripRepository
from smart_delivery_routing.domain.tracking import TrackingEventRepository
from smart_delivery_routing.domain.notification import NotificationRepository
from smart_delivery_routing.domain.shipping import ShippingRequestRepository
from smart_delivery_routing.infrastructure.fcm_notification_service import FCMNotificationService
from smart_delivery_routing.infrastructure.websocket import ConnectionManager

# TODO: restore after domain.models migration
# from smart_delivery_routing.infrastructure.job_service import CeleryRedisJobService
from smart_delivery_routing.infrastructure.supabase.auth_service import SupabaseAuthService
from smart_delivery_routing.infrastructure.supabase.client import get_supabase_client
from smart_delivery_routing.infrastructure.supabase.repositories.auth import get_user_id, get_user_role
from smart_delivery_routing.infrastructure.supabase.repositories.delivery_routes import SupabaseDeliveryRouteRepository, SupabaseRouteStopRepository
from smart_delivery_routing.infrastructure.supabase.repositories.drivers import SupabaseDriverRepository
from smart_delivery_routing.infrastructure.supabase.repositories.hubs import SupabaseHubRepository
from smart_delivery_routing.infrastructure.supabase.repositories.trucks import SupabaseTruckRepository
from smart_delivery_routing.infrastructure.supabase.repositories.notifications import SupabaseNotificationRepository
from smart_delivery_routing.infrastructure.supabase.repositories.parcels import SupabaseParcelRepository
from smart_delivery_routing.infrastructure.supabase.repositories.truck_trip_items import SupabaseTruckTripItemRepository
from smart_delivery_routing.infrastructure.supabase.repositories.truck_trips import SupabaseTruckTripRepository
from smart_delivery_routing.infrastructure.supabase.repositories.shipping_requests import SupabaseShippingRequestRepository
from smart_delivery_routing.infrastructure.supabase.repositories.tracking_events import SupabaseTrackingEventRepository

# TODO: restore after domain.models migration
# from smart_delivery_routing.application.services import DistanceCalculator, RouteSolver
# from smart_delivery_routing.application.solvers.nearest_neighbor import NearestNeighborSolver
# from smart_delivery_routing.config import OSRM_URL
# from smart_delivery_routing.domain.repositories import OrderRepository, VehicleRepository, WarehouseRepository
# from smart_delivery_routing.infrastructure.osrm.distance import OSRMDistanceCalculator
# from smart_delivery_routing.infrastructure.supabase.repositories.orders import SupabaseOrderRepository
# from smart_delivery_routing.infrastructure.supabase.repositories.vehicles import SupabaseVehicleRepository
# from smart_delivery_routing.infrastructure.supabase.repositories.warehouses import SupabaseWarehouseRepository

# _distance_calculator = OSRMDistanceCalculator(base_url=OSRM_URL)
# _solvers: list[tuple[str, RouteSolver]] = [("nearest_neighbor", NearestNeighborSolver())]
# _job_service = CeleryRedisJobService()
_auth_service = SupabaseAuthService()
_ws_manager = ConnectionManager()

_security = HTTPBearer()


def _authed_client(token: str) -> Client:
    client = get_supabase_client()
    client.postgrest.auth(token)
    return client


# TODO: restore after domain.models migration
# def get_order_repo(token=Depends(_security)) -> OrderRepository:
#     return SupabaseOrderRepository(_authed_client(token.credentials))

# def get_vehicle_repo(token=Depends(_security)) -> VehicleRepository:
#     return SupabaseVehicleRepository(_authed_client(token.credentials))

# def get_warehouse_repo(token=Depends(_security)) -> WarehouseRepository:
#     return SupabaseWarehouseRepository(_authed_client(token.credentials))


def get_parcel_repo(token=Depends(_security)) -> ParcelRepository:
    return SupabaseParcelRepository(_authed_client(token.credentials))


def get_truck_trip_repo(token=Depends(_security)) -> TruckTripRepository:
    return SupabaseTruckTripRepository(_authed_client(token.credentials))


def get_truck_trip_item_repo(token=Depends(_security)) -> TruckTripItemRepository:
    return SupabaseTruckTripItemRepository(_authed_client(token.credentials))


def get_tracking_event_repo(token=Depends(_security)) -> TrackingEventRepository:
    return SupabaseTrackingEventRepository(_authed_client(token.credentials))


def get_shipping_request_repo(token=Depends(_security)) -> ShippingRequestRepository:
    return SupabaseShippingRequestRepository(_authed_client(token.credentials))


def get_truck_repo(token=Depends(_security)) -> TruckRepository:
    return SupabaseTruckRepository(_authed_client(token.credentials))


def get_hub_repo(token=Depends(_security)) -> HubRepository:
    return SupabaseHubRepository(_authed_client(token.credentials))


def get_driver_repo(token=Depends(_security)) -> DriverRepository:
    return SupabaseDriverRepository(_authed_client(token.credentials))


def get_delivery_route_repo(token=Depends(_security)) -> DeliveryRouteRepository:
    return SupabaseDeliveryRouteRepository(_authed_client(token.credentials))


def get_route_stop_repo(token=Depends(_security)) -> RouteStopRepository:
    return SupabaseRouteStopRepository(_authed_client(token.credentials))


def get_notification_repo(token=Depends(_security)) -> NotificationRepository:
    return SupabaseNotificationRepository(_authed_client(token.credentials))


def get_notification_service(token=Depends(_security)) -> NotificationService:
    return FCMNotificationService(SupabaseNotificationRepository(_authed_client(token.credentials)))


def get_current_driver_id(token=Depends(_security)) -> str:
    return get_user_id(token.credentials)


def require_admin(token=Depends(_security)) -> None:
    if get_user_role(token.credentials) != "admin":
        raise HTTPException(status_code=403, detail="Admin required.")


def require_driver(token=Depends(_security)) -> None:
    if get_user_role(token.credentials) not in ("admin", "driver"):
        raise HTTPException(status_code=403, detail="Authentication required.")


# TODO: restore after domain.models migration
# def get_distance_calculator() -> DistanceCalculator:
#     return _distance_calculator

# def get_solvers() -> list[tuple[str, RouteSolver]]:
#     return _solvers


# TODO: restore after domain.models migration
# def get_job_service() -> JobService:
#     return _job_service


def get_auth_service() -> AuthService:
    return _auth_service


def get_ws_manager() -> ConnectionManager:
    return _ws_manager
