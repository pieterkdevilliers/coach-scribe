"""FastAPI application: route registration and ARQ pool lifespan."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import jobs, process
from app.core.queue import get_arq_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

app.include_router(process.router)
app.include_router(jobs.router)
