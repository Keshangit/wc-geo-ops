import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from rq import Queue
from redis import Redis

from api.auth import require_api_key
from api.config import get_settings
from api.schemas import FullAuditRequest, JobEnqueueResponse
from api.services.job_store import create_job, redis_available
from api.services.url_normalize import UrlValidationError, normalize_url
from api.workers.full_worker import process_full_audit

router = APIRouter(prefix="/v1/audits", tags=["audits"])
logger = logging.getLogger(__name__)


@router.post("/full", status_code=status.HTTP_202_ACCEPTED)
def full_audit(
    body: FullAuditRequest,
    _: None = Depends(require_api_key),
) -> JSONResponse:
    if not redis_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not available",
        )

    try:
        url, normalized_domain = normalize_url(body.url)
    except UrlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    domain = body.domain or normalized_domain
    job_id = create_job(url, domain, body.client_ref)

    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    queue = Queue(settings.rq_queue_name, connection=conn)
    queue.enqueue(
        process_full_audit,
        job_id,
        url,
        domain,
        body.client_ref,
        job_timeout="30m",
    )

    logger.info(
        "full_audit enqueued",
        extra={
            "job_id": job_id,
            "domain": domain,
            "client_ref": body.client_ref or "",
        },
    )

    payload = JobEnqueueResponse(
        job_id=job_id,
        status="queued",
        url=url,
        domain=domain,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=payload.model_dump(),
    )
