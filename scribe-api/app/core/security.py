"""API key verification and rate limiting for the Scribe API."""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

limiter = Limiter(key_func=get_remote_address)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> None:
    """Verify X-API-Key header. Pass-through when API_KEY is not configured."""
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
