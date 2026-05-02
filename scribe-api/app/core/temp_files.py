"""Temp file utilities for saving uploads and downloading from URLs."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import httpx
from fastapi import UploadFile

from app.core.config import settings

_CONTENT_TYPE_SUFFIXES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
}


def _temp_path(suffix: str) -> Path:
    """Return a unique path inside the configured temp directory."""
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / f"{os.urandom(8).hex()}{suffix}"


async def save_upload(file: UploadFile) -> Path:
    """Write an uploaded file to the configured temp directory and return its path."""
    suffix = Path(file.filename or "upload").suffix
    dest = _temp_path(suffix)

    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    return dest


async def download_from_url(url: str) -> Path:
    """Stream-download a file from a presigned URL into the temp directory."""
    url_path = url.split("?")[0]
    suffix = Path(url_path).suffix

    timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            if not suffix:
                content_type = response.headers.get("content-type", "").split(";")[0]
                suffix = _CONTENT_TYPE_SUFFIXES.get(content_type.strip(), ".tmp")

            dest = _temp_path(suffix)
            async with aiofiles.open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(1024 * 1024):
                    await f.write(chunk)

    return dest


@asynccontextmanager
async def temp_upload(file: UploadFile):
    """Save upload to temp dir and guarantee deletion on exit."""
    path = await save_upload(file)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
