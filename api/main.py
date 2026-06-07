from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api.config import get_settings
from api.logging_config import setup_logging
from api.routes import audits_full, audits_quick, health, jobs

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    yield


app = FastAPI(
    title="GEO Operations API",
    description=(
        "HTTP API for WC GEO audits (quick sync + full async jobs).\n\n"
        "**Swagger:** click **Authorize** (top right), paste your `OPS_API_KEY` "
        "from `.env` (value only — no `Bearer ` prefix), then Execute."
    ),
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(health.router)
app.include_router(audits_quick.router)
app.include_router(audits_full.router)
app.include_router(jobs.router)
