"""Tests for POST /ghl/feedback-review."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.ghl_client import GHLClientError


@pytest.fixture
async def ghl_client():
    """Async test client scoped to the GHL router (no pool dependency needed)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_feedback_review_accepts_immediately(ghl_client):
    """Webhook returns 200/accepted without waiting for LLM or GHL calls."""
    review_text = "I had a wonderful experience working with this team."

    with (
        patch(
            "app.api.routes.ghl._generate_review",
            new=AsyncMock(return_value=review_text),
        ) as mock_gen,
        patch(
            "app.api.routes.ghl.update_contact_review",
            new=AsyncMock(),
        ) as mock_update,
        patch(
            "app.api.routes.ghl.add_contact_tag",
            new=AsyncMock(),
        ) as mock_tag,
    ):
        resp = await ghl_client.post(
            "/ghl/feedback-review",
            json={
                "contactId": "abc123",
                "fullName": "Jane Smith",
                "What did you enjoy most?": "The structured approach to automation",
                "Overall rating?": "5 stars",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["contact_id"] == "abc123"

    # Background task ran within test response cycle
    mock_gen.assert_called_once()
    mock_update.assert_called_once_with("abc123", review_text)
    mock_tag.assert_called_once_with("abc123", "feedback summary completed")


async def test_feedback_review_missing_contact_id_returns_422(ghl_client):
    """Payload with no contactId in any form returns HTTP 422."""
    resp = await ghl_client.post(
        "/ghl/feedback-review",
        json={
            "fullName": "Jane Smith",
            "What did you enjoy?": "Everything was great!",
        },
    )
    assert resp.status_code == 422


async def test_feedback_review_ghl_failure_still_returns_200(ghl_client):
    """GHL API failure is handled in background — webhook still returns 200."""
    with (
        patch(
            "app.api.routes.ghl._generate_review",
            new=AsyncMock(return_value="Great service, highly recommend!"),
        ),
        patch(
            "app.api.routes.ghl.update_contact_review",
            new=AsyncMock(
                side_effect=GHLClientError("API returned 401: Unauthorized")
            ),
        ),
    ):
        resp = await ghl_client.post(
            "/ghl/feedback-review",
            json={
                "contactId": "abc123",
                "feedback": "The team was incredibly helpful.",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


async def test_feedback_review_contact_id_from_nested_contact(ghl_client):
    """contactId nested under contact.id is resolved correctly."""
    with (
        patch(
            "app.api.routes.ghl._generate_review",
            new=AsyncMock(return_value="Fantastic experience!"),
        ),
        patch("app.api.routes.ghl.update_contact_review", new=AsyncMock()),
        patch("app.api.routes.ghl.add_contact_tag", new=AsyncMock()),
    ):
        resp = await ghl_client.post(
            "/ghl/feedback-review",
            json={
                "contact": {"id": "nested456", "name": "Bob"},
                "How was your experience?": "Excellent",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["contact_id"] == "nested456"
