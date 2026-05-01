"""Tests for ARQ job task functions in app.core.queue."""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.queue import extract_job, process_job, transcribe_job


async def test_transcribe_job_returns_transcript(tmp_path):
    fake_file = tmp_path / "audio.wav"
    fake_file.write_bytes(b"fake audio")

    mock_svc = AsyncMock()
    mock_svc.transcribe = AsyncMock(return_value="hello world")

    with patch("app.services.transcription.transcription_service", mock_svc):
        result = await transcribe_job({}, str(fake_file), "en", False)

    assert result == {"transcript": "hello world"}


async def test_transcribe_job_deletes_file_on_success(tmp_path):
    fake_file = tmp_path / "audio.wav"
    fake_file.write_bytes(b"fake audio")

    mock_svc = AsyncMock()
    mock_svc.transcribe = AsyncMock(return_value="")

    with patch("app.services.transcription.transcription_service", mock_svc):
        await transcribe_job({}, str(fake_file), "en", False)

    assert not fake_file.exists()


async def test_transcribe_job_deletes_file_on_error(tmp_path):
    fake_file = tmp_path / "audio.wav"
    fake_file.write_bytes(b"fake audio")

    mock_svc = AsyncMock()
    mock_svc.transcribe = AsyncMock(side_effect=RuntimeError("whisper failed"))

    with patch("app.services.transcription.transcription_service", mock_svc):
        with pytest.raises(RuntimeError, match="whisper failed"):
            await transcribe_job({}, str(fake_file), "en", False)

    assert not fake_file.exists()


async def test_extract_job_returns_extraction():
    mock_svc = AsyncMock()
    mock_svc.extract = AsyncMock(return_value={"summary": "good call"})

    with patch("app.services.extraction.extraction_service", mock_svc):
        result = await extract_job({}, "the transcript", "summarise")

    assert result == {"extraction": {"summary": "good call"}}
    mock_svc.extract.assert_called_once_with("the transcript", "summarise")


async def test_process_job_returns_both(tmp_path):
    fake_file = tmp_path / "audio.wav"
    fake_file.write_bytes(b"fake audio")

    mock_trans = AsyncMock()
    mock_trans.transcribe = AsyncMock(return_value="the transcript")
    mock_extract = AsyncMock()
    mock_extract.extract = AsyncMock(return_value={"summary": "brief"})

    with (
        patch("app.services.transcription.transcription_service", mock_trans),
        patch("app.services.extraction.extraction_service", mock_extract),
    ):
        result = await process_job({}, str(fake_file), "summarise", "en")

    assert result == {"transcript": "the transcript", "extraction": {"summary": "brief"}}


async def test_process_job_deletes_file_on_error(tmp_path):
    fake_file = tmp_path / "audio.wav"
    fake_file.write_bytes(b"fake audio")

    mock_trans = AsyncMock()
    mock_trans.transcribe = AsyncMock(side_effect=RuntimeError("failed"))

    with patch("app.services.transcription.transcription_service", mock_trans):
        with pytest.raises(RuntimeError):
            await process_job({}, str(fake_file), "summarise", "en")

    assert not fake_file.exists()
