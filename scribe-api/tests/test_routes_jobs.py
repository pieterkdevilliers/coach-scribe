"""Tests for GET /job/{id} and GET /health endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arq.jobs import JobStatus as ArqJobStatus


NOW = datetime.now(timezone.utc)


def make_arq_result(*, success: bool, result, enqueue_time=NOW, finish_time=NOW):
    """Build a mock ARQ JobResult dataclass."""
    r = MagicMock()
    r.success = success
    r.result = result
    r.enqueue_time = enqueue_time
    r.finish_time = finish_time
    return r


def make_arq_info(enqueue_time=NOW):
    """Build a mock ARQ JobDef dataclass."""
    info = MagicMock()
    info.enqueue_time = enqueue_time
    return info


async def test_get_job_complete_with_transcript(api_client):
    arq_result = make_arq_result(success=True, result={"transcript": "hello world"})
    with patch("app.api.routes.jobs.Job") as MockJob:
        MockJob.return_value.result_info = AsyncMock(return_value=arq_result)
        resp = await api_client.get("/job/test-id")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert data["transcript"] == "hello world"
    assert data["extraction"] is None
    assert data["error"] is None


async def test_get_job_complete_with_extraction(api_client):
    arq_result = make_arq_result(
        success=True, result={"extraction": {"summary": "good call"}}
    )
    with patch("app.api.routes.jobs.Job") as MockJob:
        MockJob.return_value.result_info = AsyncMock(return_value=arq_result)
        resp = await api_client.get("/job/test-id")

    data = resp.json()
    assert data["status"] == "complete"
    assert data["extraction"] == {"summary": "good call"}
    assert data["transcript"] is None


async def test_get_job_failed_surfaces_error(api_client):
    arq_result = make_arq_result(
        success=False, result=ValueError("whisper crashed")
    )
    with patch("app.api.routes.jobs.Job") as MockJob:
        MockJob.return_value.result_info = AsyncMock(return_value=arq_result)
        resp = await api_client.get("/job/test-id")

    data = resp.json()
    assert data["status"] == "failed"
    assert "whisper crashed" in data["error"]
    assert data["transcript"] is None


async def test_get_job_pending(api_client):
    with patch("app.api.routes.jobs.Job") as MockJob:
        mock_job = MockJob.return_value
        mock_job.result_info = AsyncMock(return_value=None)
        mock_job.status = AsyncMock(return_value=ArqJobStatus.queued)
        mock_job.info = AsyncMock(return_value=make_arq_info())
        resp = await api_client.get("/job/test-id")

    data = resp.json()
    assert data["status"] == "pending"


async def test_get_job_processing(api_client):
    with patch("app.api.routes.jobs.Job") as MockJob:
        mock_job = MockJob.return_value
        mock_job.result_info = AsyncMock(return_value=None)
        mock_job.status = AsyncMock(return_value=ArqJobStatus.in_progress)
        mock_job.info = AsyncMock(return_value=make_arq_info())
        resp = await api_client.get("/job/test-id")

    assert resp.json()["status"] == "processing"


async def test_get_job_not_found_returns_404(api_client):
    with patch("app.api.routes.jobs.Job") as MockJob:
        mock_job = MockJob.return_value
        mock_job.result_info = AsyncMock(return_value=None)
        mock_job.status = AsyncMock(return_value=ArqJobStatus.not_found)
        resp = await api_client.get("/job/nonexistent-id")

    assert resp.status_code == 404


async def test_health_returns_ok(api_client, mock_pool):
    mock_pool.zcard = AsyncMock(return_value=2)

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=MagicMock(status_code=200))

    with patch("app.api.routes.jobs.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = await api_client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["queue_depth"] == 2
    assert data["ollama_ready"] is True


async def test_health_ollama_unreachable(api_client, mock_pool):
    import httpx

    mock_pool.zcard = AsyncMock(return_value=0)

    with patch("app.api.routes.jobs.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = await api_client.get("/health")

    data = resp.json()
    assert data["status"] == "ok"
    assert data["ollama_ready"] is False
