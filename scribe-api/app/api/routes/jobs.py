"""Routes for job polling (GET /job/{id}) and service health (GET /health)."""
import logging
from datetime import datetime, timezone

import httpx
from arq.connections import ArqRedis
from arq.jobs import Job
from arq.jobs import JobStatus as ArqJobStatus
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.queue import get_pool
from app.schemas.jobs import JobResult, JobStatus
from app.schemas.requests import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_ARQ_STATUS_MAP = {
    ArqJobStatus.queued: JobStatus.pending,
    ArqJobStatus.deferred: JobStatus.pending,
    ArqJobStatus.in_progress: JobStatus.processing,
}


@router.get("/job/{job_id}", response_model=JobResult)
async def get_job(job_id: str, pool: ArqRedis = Depends(get_pool)) -> JobResult:
    """Return the current status and result of a queued job."""
    job = Job(job_id, pool)

    result_info = await job.result_info()
    if result_info is not None:
        if result_info.success:
            data = result_info.result or {}
            return JobResult(
                job_id=job_id,
                status=JobStatus.complete,
                transcript=data.get("transcript"),
                extraction=data.get("extraction"),
                created_at=result_info.enqueue_time,
                completed_at=result_info.finish_time,
            )
        return JobResult(
            job_id=job_id,
            status=JobStatus.failed,
            error=str(result_info.result),
            created_at=result_info.enqueue_time,
            completed_at=result_info.finish_time,
        )

    arq_status = await job.status()
    if arq_status == ArqJobStatus.not_found:
        raise HTTPException(status_code=404, detail="Job not found")

    info = await job.info()
    created_at = info.enqueue_time if info else datetime.now(timezone.utc)

    return JobResult(
        job_id=job_id,
        status=_ARQ_STATUS_MAP.get(arq_status, JobStatus.pending),
        created_at=created_at,
    )


@router.get("/health", response_model=HealthResponse)
async def health(pool: ArqRedis = Depends(get_pool)) -> HealthResponse:
    """Report queue depth, Whisper load state, and Ollama reachability."""
    queue_depth = await pool.zcard(b"arq:queue")

    ollama_ready = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_ready = resp.status_code == 200
    except httpx.RequestError:
        pass

    from app.services.transcription import transcription_service

    return HealthResponse(
        status="ok",
        queue_depth=queue_depth,
        whisper_ready=transcription_service.is_loaded,
        ollama_ready=ollama_ready,
    )
