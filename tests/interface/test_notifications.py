from tests.factories import make_notification
from tests.interface.conftest import DEFAULT_DRIVER_ID


def test_list_notifications_empty(client):
    response = client.get("/notifications")
    assert response.status_code == 200
    assert response.json() == []


def test_list_notifications(client, fakes):
    notification = make_notification(driver_id=DEFAULT_DRIVER_ID)
    fakes.notification_repo._store.append(notification)
    response = client.get("/notifications")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == notification.title


def test_mark_notification_as_read(client, fakes):
    notification = make_notification(driver_id=DEFAULT_DRIVER_ID, notification_id="notif-1")
    fakes.notification_repo._store.append(notification)
    response = client.patch("/notifications/notif-1/read")
    assert response.status_code == 204
    assert fakes.notification_repo._store[0].is_read is True
