from fastapi.testclient import TestClient

from smart_delivery_routing.interface.api import app


def test_health_ok(monkeypatch):
    monkeypatch.setattr("smart_delivery_routing.interface.api.routers.health.health_check_redis", lambda: True)
    monkeypatch.setattr("smart_delivery_routing.interface.api.routers.health.health_check_supabase", lambda: True)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "ok", "supabase": "ok"}


def test_health_degraded_when_redis_down(monkeypatch):
    monkeypatch.setattr("smart_delivery_routing.interface.api.routers.health.health_check_redis", lambda: False)
    monkeypatch.setattr("smart_delivery_routing.interface.api.routers.health.health_check_supabase", lambda: True)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["redis"] == "down"
