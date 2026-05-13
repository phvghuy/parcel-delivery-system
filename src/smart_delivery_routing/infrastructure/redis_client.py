import json

import redis

from smart_delivery_routing.config import REDIS_URL

_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

_JOB_TTL = 86400       # 24 hours
_MATRIX_TTL = 86400 * 7  # 7 days
_JOB_KEY_PREFIX = "job:"
_MATRIX_KEY_PREFIX = "distance-matrix:"


def register_job(job_id: str) -> None:
    _client.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL, "submitted")


def job_exists(job_id: str) -> bool:
    return _client.exists(f"{_JOB_KEY_PREFIX}{job_id}") == 1


def get_matrix_cache(key: str) -> list[list[float]] | None:
    value = _client.get(f"{_MATRIX_KEY_PREFIX}{key}")
    return json.loads(value) if value else None


def set_matrix_cache(key: str, matrix: list[list[float]]) -> None:
    _client.setex(f"{_MATRIX_KEY_PREFIX}{key}", _MATRIX_TTL, json.dumps(matrix))
