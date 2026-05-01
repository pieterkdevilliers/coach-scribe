"""ARQ job task functions and Redis pool helpers."""
import logging
from pathlib import Path

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_redis_settings() -> RedisSettings:
    """Build ARQ RedisSettings from the configured REDIS_URL."""
    return RedisSettings.from_dsn(settings.redis_url)


async def get_arq_pool() -> ArqRedis:
    """Open a new ARQ connection pool; called once at startup via lifespan."""
    return await create_pool(get_redis_settings())


async def get_pool(request: Request) -> ArqRedis:
    """FastAPI dependency that returns the shared ARQ pool from app.state."""
    return request.app.state.arq_pool


# ---------------------------------------------------------------------------
# Job task functions — executed by the ARQ worker
# ---------------------------------------------------------------------------

async def transcribe_job(
    _ctx: dict, file_path: str, language: str, timestamps: bool
) -> dict:
    """ARQ job: transcribe the file at file_path and delete it when done."""
    from app.services.transcription import transcription_service

    path = Path(file_path)
    try:
        logger.info("transcribe_job started: %s", path.name)
        transcript = await transcription_service.transcribe(path, language, timestamps)
        logger.info("transcribe_job complete: %s", path.name)
        return {"transcript": transcript}
    finally:
        path.unlink(missing_ok=True)


async def extract_job(_ctx: dict, transcript: str, prompt: str) -> dict:
    """ARQ job: run LLM extraction on an existing transcript."""
    from app.services.extraction import extraction_service

    logger.info("extract_job started")
    extraction = await extraction_service.extract(transcript, prompt)
    logger.info("extract_job complete")
    return {"extraction": extraction}


async def process_job(_ctx: dict, file_path: str, prompt: str, language: str) -> dict:
    """ARQ job: transcribe a file then immediately run LLM extraction."""
    from app.services.extraction import extraction_service
    from app.services.transcription import transcription_service

    path = Path(file_path)
    try:
        logger.info("process_job transcribing: %s", path.name)
        transcript = await transcription_service.transcribe(path, language)
        logger.info("process_job extracting: %s", path.name)
        extraction = await extraction_service.extract(transcript, prompt)
        logger.info("process_job complete: %s", path.name)
        return {"transcript": transcript, "extraction": extraction}
    finally:
        path.unlink(missing_ok=True)
