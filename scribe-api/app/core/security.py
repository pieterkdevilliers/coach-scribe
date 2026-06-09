"""API key verification and rate limiting for the Scribe API."""
from fastapi import HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

limiter = Limiter(key_func=get_remote_address)


async def verify_api_key(
    header_key: str | None = Security(api_key_header),
    query_key: str | None = Query(default=None, alias="api_key"),
) -> None:
    """Verify API key from X-API-Key header or ?api_key= query param."""
    if not settings.api_key:
        return
    provided = header_key or query_key
    if provided != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
