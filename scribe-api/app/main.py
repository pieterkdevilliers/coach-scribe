"""FastAPI application: route registration and ARQ pool lifespan."""
import logging
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import jobs, process
from app.core.config import settings
from app.core.queue import get_arq_pool
from app.core.security import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if settings.logfire_token:
    logfire.configure(service_name="scribe-api")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Manage the ARQ pool connection across the application lifecycle."""
    logger.info("Scribe API starting up")
    fastapi_app.state.arq_pool = await get_arq_pool()
    yield
    await fastapi_app.state.arq_pool.aclose()
    logger.info("Scribe API shutting down")


app = FastAPI(
    title="Scribe API",
    description="Local audio/video transcription and extraction service",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.logfire_token:
    logfire.instrument_fastapi(app)
    logfire.instrument_httpx()
    logfire.instrument_pydantic_ai()

app.include_router(process.router)
app.include_router(jobs.router)
