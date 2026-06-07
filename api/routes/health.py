from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "geo-ops-api",
        "version": "1.0.0",
    }
