"""ARQ worker entrypoint — run with: uv run arq worker.WorkerSettings."""
import logfire
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.queue import (
    extract_job,
    process_job,
    process_url_job,
    transcribe_job,
    transcribe_url_job,
)

if settings.logfire_token:
    logfire.configure(service_name="scribe-worker")


class WorkerSettings:
    """ARQ worker: job functions, Redis settings, and concurrency limits."""

    functions = [
        transcribe_job,
        extract_job,
        process_job,
        transcribe_url_job,
        process_url_job,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 3600  # 60 min — long CPU transcription jobs
