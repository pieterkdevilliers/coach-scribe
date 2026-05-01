from pydantic import BaseModel


class ExtractRequest(BaseModel):
    """Request body for POST /extract."""

    transcript: str
    prompt: str


class ProcessRequest(BaseModel):
    """Request body fields for POST /process."""

    prompt: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    queue_depth: int
    whisper_ready: bool
    ollama_ready: bool
