"""GHL API client for updating contacts and adding tags."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GHL_BASE = "https://services.leadconnectorhq.com"
_GHL_VERSION = "2021-07-28"


class GHLClientError(Exception):
    """Raised when a GHL API call returns a non-2xx response."""


def _headers() -> dict[str, str]:
    """Build GHL request headers."""
    return {
        "Authorization": f"Bearer {settings.ghl_api_key}",
        "Version": _GHL_VERSION,
        "Content-Type": "application/json",
    }


async def update_contact_review(contact_id: str, review_text: str) -> None:
    """PUT feedback_summary_review custom field on a GHL contact."""
    url = f"{_GHL_BASE}/contacts/{contact_id}"
    payload = {
        "customFields": [
            {"key": "feedback_summary_review", "field_value": review_text}
        ]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(url, json=payload, headers=_headers())
    if resp.is_error:
        logger.error(
            "GHL update_contact failed for %s: %s %s",
            contact_id,
            resp.status_code,
            resp.text,
        )
        raise GHLClientError(
            f"update contact {contact_id} returned {resp.status_code}: {resp.text}"
        )
    logger.info("GHL contact %s custom field updated", contact_id)


async def add_contact_tag(contact_id: str, tag: str) -> None:
    """POST a tag to a GHL contact."""
    url = f"{_GHL_BASE}/contacts/{contact_id}/tags"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json={"tags": [tag]}, headers=_headers())
    if resp.is_error:
        logger.error(
            "GHL add_tag failed for %s: %s %s",
            contact_id,
            resp.status_code,
            resp.text,
        )
        raise GHLClientError(
            f"add tag for {contact_id} returned {resp.status_code}: {resp.text}"
        )
    logger.info("GHL contact %s tagged: %s", contact_id, tag)
