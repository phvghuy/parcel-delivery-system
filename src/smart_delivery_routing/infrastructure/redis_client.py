import json

import redis

from smart_delivery_routing.config import REDIS_URL

_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

_JOB_TTL = 86400       # 24 hours
_MATRIX_TTL = 86400 * 7  # 7 days
_JOB_KEY_PREFIX = "job:"
_MATRIX_KEY_PREFIX = "distance-matrix:"
_HUB_CACHE_KEY = "hubs:active_list"
_HUB_TTL = 300 # 5 mins


def health_check_redis() -> bool:
    return bool(_client.ping())


def get_hub_cache() -> list[dict] | None:
    value = _client.get(_HUB_CACHE_KEY)
    return json.loads(value) if value else None


def set_hub_cache(rows: list[dict]) -> None:
    _client.setex(_HUB_CACHE_KEY, _HUB_TTL, json.dumps(rows))


def invalidate_hub_cache() -> None:
    _client.delete(_HUB_CACHE_KEY)


def register_job(job_id: str) -> None:
    _client.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL, "submitted")


def job_exists(job_id: str) -> bool:
    return _client.exists(f"{_JOB_KEY_PREFIX}{job_id}") == 1


def get_matrix_cache(key: str) -> list[list[float]] | None:
    value = _client.get(f"{_MATRIX_KEY_PREFIX}{key}")
    return json.loads(value) if value else None


def set_matrix_cache(key: str, matrix: list[list[float]]) -> None:
    try:
        _client.setex(f"{_MATRIX_KEY_PREFIX}{key}", _MATRIX_TTL, json.dumps(matrix))
        print(f"[redis] cached distance matrix key={key[:8]}... size={len(matrix)}x{len(matrix[0])}", flush=True)
    except Exception as e:
        print(f"[redis] set_matrix_cache failed: {type(e).__name__}: {e}", flush=True)
