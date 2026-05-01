from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    """Lifecycle states a job moves through from creation to completion."""

    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class JobResult(BaseModel):
    """Full response body returned when polling GET /job/{id}."""

    job_id: str
    status: JobStatus
    transcript: str | None = None
    extraction: dict | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class JobEnqueued(BaseModel):
    """Response body for all POST endpoints that queue a new job."""

    job_id: str
