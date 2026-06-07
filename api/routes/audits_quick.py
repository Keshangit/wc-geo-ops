import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import require_api_key
from api.config import get_settings
from api.schemas import QuickAuditRequest
from api.services.quick_audit import QuickAuditFetchError, run_quick_audit
from api.services.url_normalize import UrlValidationError

router = APIRouter(prefix="/v1/audits", tags=["audits"])
logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


@router.post("/quick")
async def quick_audit(
    body: QuickAuditRequest,
    _: None = Depends(require_api_key),
) -> dict:
    settings = get_settings()
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor, partial(run_quick_audit, body.url)
            ),
            timeout=settings.quick_audit_timeout,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Quick audit exceeded {settings.quick_audit_timeout}s",
        )
    except UrlValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except QuickAuditFetchError as e:
        logger.warning("quick_audit fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
