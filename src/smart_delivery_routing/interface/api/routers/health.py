from fastapi import APIRouter
from fastapi.responses import JSONResponse
from smart_delivery_routing.infrastructure.redis_client import health_check_redis
from smart_delivery_routing.infrastructure.supabase.health import health_check_supabase


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    redis_ok = health_check_redis()
    supabase_ok = health_check_supabase()
    all_ok = redis_ok and supabase_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ok" if all_ok else "degraded",
            "redis": "ok" if redis_ok else "down",
            "supabase": "ok" if supabase_ok else "down",
        }
    )
