from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException

from smart_delivery_routing.infrastructure.celery import celery_app
from smart_delivery_routing.infrastructure.redis_client import job_exists
from ..dependencies import require_admin
from ..schemas import JobStatusResponse

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, _: None = Depends(require_admin)) -> JobStatusResponse:
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        # result_expires đã qua nhưng job key (24h) vẫn còn
        if result.date_done is None:
            return JobStatusResponse(job_id=job_id, status="pending")
        return JobStatusResponse(job_id=job_id, status="expired")

    if result.state == "FAILURE":
        return JobStatusResponse(job_id=job_id, status="failure", error=str(result.info))

    return JobStatusResponse(job_id=job_id, status="success", result=result.result)
