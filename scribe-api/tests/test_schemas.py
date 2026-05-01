"""Tests for Pydantic schema models."""
from datetime import datetime, timezone

import pytest

from app.schemas.jobs import JobEnqueued, JobResult, JobStatus
from app.schemas.requests import ExtractRequest, HealthResponse, ProcessRequest


def test_job_status_values():
    """Enum values match the string literals used in the API contract."""
    assert JobStatus.pending == "pending"
    assert JobStatus.processing == "processing"
    assert JobStatus.complete == "complete"
    assert JobStatus.failed == "failed"


def test_job_result_optional_fields_default_to_none():
    now = datetime.now(timezone.utc)
    result = JobResult(job_id="abc", status=JobStatus.pending, created_at=now)
    assert result.transcript is None
    assert result.extraction is None
    assert result.error is None
    assert result.completed_at is None


def test_job_result_complete_with_transcript():
    now = datetime.now(timezone.utc)
    result = JobResult(
        job_id="abc",
        status=JobStatus.complete,
        transcript="hello world",
        created_at=now,
        completed_at=now,
    )
    assert result.transcript == "hello world"
    assert result.extraction is None


def test_job_result_complete_with_extraction():
    now = datetime.now(timezone.utc)
    result = JobResult(
        job_id="abc",
        status=JobStatus.complete,
        extraction={"summary": "test", "score": 9},
        created_at=now,
        completed_at=now,
    )
    assert result.extraction == {"summary": "test", "score": 9}
    assert result.transcript is None


def test_job_result_failed_with_error():
    now = datetime.now(timezone.utc)
    result = JobResult(
        job_id="abc",
        status=JobStatus.failed,
        error="something went wrong",
        created_at=now,
        completed_at=now,
    )
    assert result.error == "something went wrong"


def test_job_enqueued():
    enqueued = JobEnqueued(job_id="xyz-123")
    assert enqueued.job_id == "xyz-123"


def test_extract_request_requires_both_fields():
    req = ExtractRequest(transcript="the text", prompt="summarise")
    assert req.transcript == "the text"
    assert req.prompt == "summarise"


def test_extract_request_missing_prompt_raises():
    with pytest.raises(Exception):
        ExtractRequest(transcript="the text")


def test_process_request():
    req = ProcessRequest(prompt="give me a summary")
    assert req.prompt == "give me a summary"


def test_health_response():
    resp = HealthResponse(
        status="ok", queue_depth=3, whisper_ready=True, ollama_ready=False
    )
    assert resp.status == "ok"
    assert resp.queue_depth == 3
    assert resp.whisper_ready is True
    assert resp.ollama_ready is False
