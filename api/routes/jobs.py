from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import require_api_key
from api.services.job_store import get_job

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job_status(
    job_id: str,
    _: None = Depends(require_api_key),
) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    if job.get("report") == "":
        job["report"] = None
    return job
