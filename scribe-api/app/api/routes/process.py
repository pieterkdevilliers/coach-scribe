"""Routes for queuing new jobs: POST /transcribe, /extract, /process."""
import logging

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.queue import get_pool
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
async def transcribe(
    file: UploadFile,
    language: str = Form(default="en"),
    timestamps: bool = Form(default=False),
    pool: ArqRedis = Depends(get_pool),
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
            "transcribe_job", str(file_path), language, timestamps
        )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    logger.info("Enqueued transcribe_job %s for %s", job.job_id, file.filename)
    return JobEnqueued(job_id=job.job_id)


@router.post("/extract", response_model=JobEnqueued)
async def extract(
    body: ExtractRequest, pool: ArqRedis = Depends(get_pool)
) -> JobEnqueued:
    """Accept a transcript and prompt and enqueue an LLM extraction job."""
    job = await pool.enqueue_job("extract_job", body.transcript, body.prompt)
    logger.info("Enqueued extract_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)


@router.post("/transcribe-url", response_model=JobEnqueued)
async def transcribe_url(
    body: TranscribeUrlRequest, pool: ArqRedis = Depends(get_pool)
) -> JobEnqueued:
    """Accept a presigned URL and enqueue a transcription job."""
    job = await pool.enqueue_job(
        "transcribe_url_job", body.s3_url, body.language, body.timestamps
    )
    logger.info("Enqueued transcribe_url_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)


@router.post("/process-url", response_model=JobEnqueued)
async def process_url(
    body: ProcessUrlRequest, pool: ArqRedis = Depends(get_pool)
) -> JobEnqueued:
    """Accept a presigned URL and enqueue a combined transcription + extraction job."""
    job = await pool.enqueue_job(
        "process_url_job", body.s3_url, body.prompt, body.language
    )
    logger.info("Enqueued process_url_job %s", job.job_id)
    return JobEnqueued(job_id=job.job_id)


@router.post("/process", response_model=JobEnqueued)
async def process(
    file: UploadFile,
    prompt: str = Form(...),
    language: str = Form(default="en"),
    pool: ArqRedis = Depends(get_pool),
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
            "process_job", str(file_path), prompt, language
        )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    logger.info("Enqueued process_job %s for %s", job.job_id, file.filename)
    return JobEnqueued(job_id=job.job_id)
