import json

import smart_delivery_routing.infrastructure.redis_client as redis_client


class FakeRedis:
    def __init__(self):
        self._store: dict[str, str] = {}
        self.ping_result = True

    def ping(self) -> bool:
        return self.ping_result

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0


def test_health_check_redis_ok(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_client", fake)
    assert redis_client.health_check_redis() is True


def test_health_check_redis_down(monkeypatch):
    fake = FakeRedis()
    fake.ping_result = False
    monkeypatch.setattr(redis_client, "_client", fake)
    assert redis_client.health_check_redis() is False


def test_hub_cache_round_trip(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_client", fake)
    assert redis_client.get_hub_cache() is None
    redis_client.set_hub_cache([{"id": "1", "name": "Hub A"}])
    assert redis_client.get_hub_cache() == [{"id": "1", "name": "Hub A"}]
    redis_client.invalidate_hub_cache()
    assert redis_client.get_hub_cache() is None


def test_job_register_and_exists(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_client", fake)
    assert redis_client.job_exists("job-1") is False
    redis_client.register_job("job-1")
    assert redis_client.job_exists("job-1") is True


def test_matrix_cache_round_trip(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_client", fake)
    assert redis_client.get_matrix_cache("key-1") is None
    redis_client.set_matrix_cache("key-1", [[0.0, 1.0], [1.0, 0.0]])
    assert redis_client.get_matrix_cache("key-1") == [[0.0, 1.0], [1.0, 0.0]]


def test_set_matrix_cache_swallows_errors(monkeypatch):
    class BrokenRedis(FakeRedis):
        def setex(self, key, ttl, value):
            raise ConnectionError("redis down")

    monkeypatch.setattr(redis_client, "_client", BrokenRedis())
    redis_client.set_matrix_cache("key-1", [[0.0]])  # must not raise
