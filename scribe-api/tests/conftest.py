"""Shared pytest fixtures for the Scribe API test suite."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_pool():
    """AsyncMock ARQ pool with a pre-configured enqueue_job return value."""
    pool = AsyncMock()
    mock_job = MagicMock()
    mock_job.job_id = "test-job-id-123"
    pool.enqueue_job = AsyncMock(return_value=mock_job)
    pool.zcard = AsyncMock(return_value=0)
    return pool


@pytest.fixture
async def api_client(mock_pool):
    """Async test client with the ARQ pool replaced by mock_pool."""
    from app.core.queue import get_pool

    app.dependency_overrides[get_pool] = lambda: mock_pool
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
