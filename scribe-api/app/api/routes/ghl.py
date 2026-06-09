"""GHL webhook endpoint: POST /ghl/feedback-review."""
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from app.core.security import verify_api_key
from app.services.ghl_client import (
    GHLClientError,
    add_contact_tag,
    update_contact_review,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_REVIEW_PROMPT = (
    "You are helping a business generate a Google Review"
    " based on customer feedback answers.\n\n"
    "Below are the customer's feedback answers:\n"
    "{feedback_content}\n\n"
    "Write a single, natural-sounding Google Review in the first person, as if the "
    "customer wrote it themselves. The review should:\n"
    "- Be 3-5 sentences long\n"
    "- Sound genuine and specific, not generic\n"
    "- Highlight the most positive aspects mentioned in the feedback\n"
    "- Be suitable to publish directly as a Google Review\n\n"
    "Return ONLY the review text. No preamble, no explanation, no quotation marks "
    "around the review."
)


class GHLWebhookPayload(BaseModel):
    """Flexible GHL webhook payload; unknown fields are captured as feedback answers."""

    model_config = ConfigDict(extra="allow")

    contactId: str | None = None
    contact_id: str | None = None
    fullName: str | None = None
    full_name: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    contact: dict[str, Any] | None = None


def _resolve_contact_id(payload: GHLWebhookPayload) -> str | None:
    """Return the first non-empty contact ID found in the payload."""
    if payload.contactId:
        return payload.contactId
    if payload.contact_id:
        return payload.contact_id
    if isinstance(payload.contact, dict):
        return payload.contact.get("id")
    return None


def _build_feedback_content(payload: GHLWebhookPayload) -> str:
    """Build feedback string from customData if present, else fall back to extras."""
    extras = payload.model_extra or {}

    # GHL sends a clean customData dict — prefer it over raw extra fields
    custom_data = extras.get("customData")
    if isinstance(custom_data, dict):
        lines = [
            f"{k}: {v}"
            for k, v in custom_data.items()
            if v is not None and str(v).strip()
        ]
        if lines:
            return "\n".join(lines)

    # Fallback: use top-level extra fields, skipping known non-feedback keys
    _SKIP = frozenset({
        "first_name", "last_name", "email", "phone", "tags", "country",
        "timezone", "date_created", "full_address", "contact_type",
        "location", "workflow", "triggerData", "customData",
        "Business Sector", "Feedback Summary Review",
    })
    lines = [
        f"{k}: {v}"
        for k, v in extras.items()
        if k not in _SKIP and v is not None and str(v).strip()
    ]
    return "\n".join(lines) if lines else "(no feedback fields provided)"


async def _generate_review(feedback_content: str) -> str:
    """Call Ollama to generate a Google Review from feedback content."""
    prompt = _REVIEW_PROMPT.format(feedback_content=feedback_content)
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": settings.llm_model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
    return resp.json()["response"].strip()


async def _process_feedback_review(
    contact_id: str, feedback_content: str
) -> None:
    """Generate a Google Review and update the GHL contact (runs in background)."""
    try:
        review = await _generate_review(feedback_content)
    except Exception as exc:
        logger.exception(
            "LLM generation failed for contact %s: %s", contact_id, exc
        )
        return

    logger.info("Generated review for contact %s: %.80s...", contact_id, review)

    try:
        await update_contact_review(contact_id, review)
        await add_contact_tag(contact_id, "feedback summary completed")
    except GHLClientError as exc:
        logger.error("GHL update failed for contact %s: %s", contact_id, exc)


@router.post("/feedback-review")
async def feedback_review(
    payload: GHLWebhookPayload,
    background_tasks: BackgroundTasks,
    x_ghl_signature: str | None = Header(default=None),
    _: None = Depends(verify_api_key),
) -> dict:
    """Accept GHL webhook immediately and process review generation in background."""
    logger.info("GHL webhook received. Raw payload: %s", payload.model_dump())

    if x_ghl_signature:
        # TODO: implement HMAC validation once GHL signature details are confirmed
        logger.info("X-GHL-Signature present: %s", x_ghl_signature)

    contact_id = _resolve_contact_id(payload)
    if not contact_id:
        raise HTTPException(status_code=422, detail="contactId is required")

    feedback_content = _build_feedback_content(payload)
    logger.info(
        "Contact %s — queuing background review generation", contact_id
    )

    background_tasks.add_task(_process_feedback_review, contact_id, feedback_content)

    return {"status": "accepted", "contact_id": contact_id}
