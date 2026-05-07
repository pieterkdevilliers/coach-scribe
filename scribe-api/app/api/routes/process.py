"""Routes for queuing new jobs: POST /transcribe, /extract, /process."""
import logging

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile

from app.core.config import settings
from app.core.queue import get_pool
from app.core.security import limiter, verify_api_key
from app.core.temp_files import save_upload
from app.schemas.jobs import JobEnqueued
from app.schemas.requests import (
    ExtractRequest,
    ProcessUrlRequest,
    TranscribeUrlRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transcribe", response_model=JobEnqueued)
@limiter.limit(settings.rate_limit)
async def transcribe(
    request: Request,
    file: UploadFile,
    language: str = Form(default="en"),
    timestamps: bool = Form(default=False),
    diarize: bool = Form(default=True),
    pool: ArqRedis = Depends(get_pool),
    _: None = Depends(verify_api_key),
) -> JobEnqueued:
    """Save upload to temp storage and enqueue a transcription job."""
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit",
        )

    file_path = await save_upload(file)
    try:
        job = await pool.enqueue_job(
            "transcribe_job", str(file_path), language, timestamps, diarize
        )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    logger.info("Enqueued transcribe_job %s for %s", job.job_id, file.filename)
    return JobEnqueued(job_id=job.job_id)


@router.post("/transcribe-url", response_model=JobEnqueued)
@limiter.limit(settings.rate_limit)
async def transcribe_url(
    request: Request,
    body: TranscribeUrlRequest,
    pool: ArqRedis = Depends(get_pool),
    _: None = Depends(verify_api_key),
) -> JobEnqueued:
    """Accept a presigned URL and enqueue a transcription job."""
    job = await pool.enqueue_job(
        "transcribe_url_job", body.s3_url, body.language, body.timestamps, body.diarize
    )
    logger.info("Enqueued transcribe_url_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)


@router.post("/extract", response_model=JobEnqueued)
@limiter.limit(settings.rate_limit)
async def extract(
    request: Request,
    body: ExtractRequest,
    pool: ArqRedis = Depends(get_pool),
    _: None = Depends(verify_api_key),
) -> JobEnqueued:
    """Accept a transcript and prompt and enqueue an LLM extraction job."""
    job = await pool.enqueue_job("extract_job", body.transcript, body.prompt)
    logger.info("Enqueued extract_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)


@router.post("/process", response_model=JobEnqueued)
@limiter.limit(settings.rate_limit)
async def process(
    request: Request,
    file: UploadFile,
    prompt: str = Form(...),
    language: str = Form(default="en"),
    diarize: bool = Form(default=True),
    pool: ArqRedis = Depends(get_pool),
    _: None = Depends(verify_api_key),
) -> JobEnqueued:
    """Enqueue a combined transcription + extraction job for the uploaded file."""
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit",
        )

    file_path = await save_upload(file)
    try:
        job = await pool.enqueue_job(
            "process_job", str(file_path), prompt, language, diarize
        )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    logger.info("Enqueued process_job %s for %s", job.job_id, file.filename)
    return JobEnqueued(job_id=job.job_id)


@router.post("/process-url", response_model=JobEnqueued)
@limiter.limit(settings.rate_limit)
async def process_url(
    request: Request,
    body: ProcessUrlRequest,
    pool: ArqRedis = Depends(get_pool),
    _: None = Depends(verify_api_key),
) -> JobEnqueued:
    """Accept a presigned URL and enqueue a combined transcription + extraction job."""
    job = await pool.enqueue_job(
        "process_url_job", body.s3_url, body.prompt, body.language, body.diarize
    )
    logger.info("Enqueued process_url_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)
