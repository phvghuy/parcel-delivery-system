from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo
from httpx import TimeoutException, NetworkError, HTTPStatusError
from celery import Task

from smart_delivery_routing.application.delivery_route_use_cases import create_delivery_routes
from smart_delivery_routing.application import shipping_use_cases
from smart_delivery_routing.config import OSRM_URL
from smart_delivery_routing.infrastructure.celery import celery_app
from smart_delivery_routing.infrastructure.fcm_notification_service import FCMNotificationService
from smart_delivery_routing.infrastructure.osrm.distance import OSRMDistanceCalculator
from smart_delivery_routing.infrastructure.supabase.client import get_supabase_service_client
from smart_delivery_routing.infrastructure.supabase.repositories.delivery_routes import (
    SupabaseDeliveryRouteRepository, SupabaseRouteStopRepository,
)
from smart_delivery_routing.infrastructure.supabase.repositories.drivers import SupabaseDriverRepository
from smart_delivery_routing.infrastructure.supabase.repositories.hubs import SupabaseHubRepository
from smart_delivery_routing.infrastructure.supabase.repositories.notifications import SupabaseNotificationRepository
from smart_delivery_routing.infrastructure.supabase.repositories.parcels import SupabaseParcelRepository
from smart_delivery_routing.infrastructure.supabase.repositories.shipping_requests import SupabaseShippingRequestRepository
from smart_delivery_routing.infrastructure.supabase.repositories.tracking_events import SupabaseTrackingEventRepository

from smart_delivery_routing.domain.shipping import ShippingRequestStatus


_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_distance_calculator = OSRMDistanceCalculator(base_url=OSRM_URL)


class ShippingRequestTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        request_id = UUID(args[0])
        client = get_supabase_service_client()
        shipping_use_cases.update_shipping_status(
            request_id=request_id,
            new_status=ShippingRequestStatus.FAILED,
            repo=SupabaseShippingRequestRepository(client),
        )


@celery_app.task(
    name="handle_shipping_request", 
    autoretry_for=(TimeoutException, NetworkError),
    bind=True,
    retry_kwargs={'max_retries': 5},
    default_retry_delay=10*60,
    base=ShippingRequestTask
    )
def handle_shipping_request(self, request_id: str) -> None:
    try:
        client = get_supabase_service_client()
        shipping_use_cases.process_shipping_request(
            request_id=UUID(request_id),
            shipping_repo=SupabaseShippingRequestRepository(client),
            hub_repo=SupabaseHubRepository(client),
            parcel_repo=SupabaseParcelRepository(client),
            tracking_repo=SupabaseTrackingEventRepository(client),
        )
    except HTTPStatusError as e:
        if e.response.status_code >= 500:
            raise self.retry(exc=e)
        else:
            raise


@celery_app.task(name="create_delivery_routes")
def run_create_delivery_routes() -> None:
    now_vn = datetime.now(_VN_TZ)
    if not (8 <= now_vn.hour < 18):
        return

    client = get_supabase_service_client()

    parcel_repo = SupabaseParcelRepository(client)
    driver_repo = SupabaseDriverRepository(client)
    shipping_request_repo = SupabaseShippingRequestRepository(client)
    route_repo = SupabaseDeliveryRouteRepository(client)
    stop_repo = SupabaseRouteStopRepository(client)
    notification_service = FCMNotificationService(SupabaseNotificationRepository(client))

    routes = create_delivery_routes(
        parcel_repo=parcel_repo,
        driver_repo=driver_repo,
        shipping_request_repo=shipping_request_repo,
        route_repo=route_repo,
        stop_repo=stop_repo,
        distance_calculator=_distance_calculator,
    )

    for route in routes:
        driver = driver_repo.get_by_id(route.driver_id)
        if driver is None or not driver.fcm_token:
            continue
        stops = stop_repo.list_by_route_id(route.id)
        notification_service.send_route_notification(
            driver_id=str(route.driver_id),
            fcm_token=driver.fcm_token,
            vehicle_id=str(route.id),
            stops_count=len(stops),
            distance_km=route.total_distance_km,
            job_id=str(route.id),
        )