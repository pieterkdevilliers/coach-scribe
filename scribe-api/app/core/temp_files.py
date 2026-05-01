import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import settings


async def save_upload(file: UploadFile) -> Path:
    """Write an uploaded file to the configured temp directory and return its path."""
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "upload").suffix
    dest = temp_dir / f"{os.urandom(8).hex()}{suffix}"

    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
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
