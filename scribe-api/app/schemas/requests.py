from pydantic import BaseModel


class ExtractRequest(BaseModel):
    """Request body for POST /extract."""

    transcript: str
    prompt: str


class ProcessRequest(BaseModel):
    """Request body fields for POST /process."""

    prompt: str


class TranscribeUrlRequest(BaseModel):
    """Request body for POST /transcribe-url."""

    s3_url: str
    language: str = "en"
    timestamps: bool = False
    diarize: bool = True


class ProcessUrlRequest(BaseModel):
    """Request body for POST /process-url."""

    s3_url: str
    prompt: str
    language: str = "en"
    diarize: bool = True


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    queue_depth: int
    whisper_ready: bool
    ollama_ready: bool
