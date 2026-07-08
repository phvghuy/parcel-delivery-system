import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from smart_delivery_routing.interface.api import app


def test_ws_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(
        "smart_delivery_routing.interface.api.routers.ws.get_user_role", lambda token: "driver"
    )
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=x"):
            pass
    assert exc_info.value.code == 4403


def test_ws_accepts_admin(monkeypatch):
    monkeypatch.setattr(
        "smart_delivery_routing.interface.api.routers.ws.get_user_role", lambda token: "admin"
    )
    client = TestClient(app)
    with client.websocket_connect("/ws?token=x") as ws:
        ws.close()
