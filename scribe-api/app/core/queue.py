"""ARQ job task functions and Redis pool helpers."""
import logging
from pathlib import Path

import logfire
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
    with logfire.span("transcribe_job", file=path.name, language=language):
        try:
            logger.info("transcribe_job started: %s", path.name)
            transcript = await transcription_service.transcribe(
                path, language, timestamps
            )
            logger.info("transcribe_job complete: %s", path.name)
            return {"transcript": transcript}
        finally:
            path.unlink(missing_ok=True)


async def extract_job(_ctx: dict, transcript: str, prompt: str) -> dict:
    """ARQ job: run LLM extraction on an existing transcript."""
    from app.services.extraction import extraction_service

    with logfire.span("extract_job"):
        logger.info("extract_job started")
        extraction = await extraction_service.extract(transcript, prompt)
        logger.info("extract_job complete")
        return {"extraction": extraction}


async def process_job(_ctx: dict, file_path: str, prompt: str, language: str) -> dict:
    """ARQ job: transcribe a file then immediately run LLM extraction."""
    from app.services.extraction import extraction_service
    from app.services.transcription import transcription_service

    path = Path(file_path)
    with logfire.span("process_job", file=path.name, language=language):
        try:
            logger.info("process_job transcribing: %s", path.name)
            transcript = await transcription_service.transcribe(path, language)
            logger.info("process_job extracting: %s", path.name)
            extraction = await extraction_service.extract(transcript, prompt)
            logger.info("process_job complete: %s", path.name)
            return {"transcript": transcript, "extraction": extraction}
        finally:
            path.unlink(missing_ok=True)


async def transcribe_url_job(
    _ctx: dict, url: str, language: str, timestamps: bool
) -> dict:
    """ARQ job: download from URL, transcribe, and delete the temp file."""
    from app.core.temp_files import download_from_url
    from app.services.transcription import transcription_service

    with logfire.span("transcribe_url_job", language=language):
        path = await download_from_url(url)
        try:
            logger.info("transcribe_url_job started: %s", path.name)
            transcript = await transcription_service.transcribe(
                path, language, timestamps
            )
            logger.info("transcribe_url_job complete: %s", path.name)
            return {"transcript": transcript}
        finally:
            path.unlink(missing_ok=True)


async def process_url_job(
    _ctx: dict, url: str, prompt: str, language: str
) -> dict:
    """ARQ job: download from URL, transcribe, then run LLM extraction."""
    from app.core.temp_files import download_from_url
    from app.services.extraction import extraction_service
    from app.services.transcription import transcription_service

    with logfire.span("process_url_job", language=language):
        path = await download_from_url(url)
        try:
            logger.info("process_url_job transcribing: %s", path.name)
            transcript = await transcription_service.transcribe(path, language)
            logger.info("process_url_job extracting: %s", path.name)
            extraction = await extraction_service.extract(transcript, prompt)
            logger.info("process_url_job complete: %s", path.name)
            return {"transcript": transcript, "extraction": extraction}
        finally:
            path.unlink(missing_ok=True)
