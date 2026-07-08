from fastapi import APIRouter, Depends
from pydantic import BaseModel

from smart_delivery_routing.domain.notification import Notification, NotificationRepository
from ..dependencies import get_current_driver_id, get_notification_repo, require_driver

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    notification_id: str
    title: str
    body: str
    data: dict
    is_read: bool
    created_at: str


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        notification_id=n.notification_id,
        title=n.title,
        body=n.body,
        data=n.data,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    driver_id: str = Depends(get_current_driver_id),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    _: None = Depends(require_driver),
) -> list[NotificationResponse]:
    return [_to_response(n) for n in notification_repo.get_by_driver(driver_id)]


@router.patch("/{notification_id}/read", status_code=204)
def mark_as_read(
    notification_id: str,
    driver_id: str = Depends(get_current_driver_id),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    _: None = Depends(require_driver),
) -> None:
    notification_repo.mark_as_read(notification_id, driver_id)
