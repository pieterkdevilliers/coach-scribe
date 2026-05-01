"""Tests for TranscriptionService."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.transcription import TranscriptionService


def make_segment(text: str, start: float = 0.0, end: float = 1.0) -> MagicMock:
    """Build a mock faster-whisper segment."""
    seg = MagicMock()
    seg.text = text
    seg.start = start
    seg.end = end
    return seg


def make_service_with_model(*segments) -> TranscriptionService:
    """Return a TranscriptionService whose model is pre-loaded with mock segments."""
    svc = TranscriptionService()
    mock_model = MagicMock()
    mock_model.transcribe = MagicMock(return_value=(iter(segments), MagicMock()))
    svc._model = mock_model
    return svc


def test_is_loaded_before_model_load():
    svc = TranscriptionService()
    assert svc.is_loaded is False


def test_is_loaded_after_model_load():
    svc = TranscriptionService()
    with patch("faster_whisper.WhisperModel"):
        svc._load_model()
    assert svc.is_loaded is True


async def test_transcribe_joins_segment_text():
    svc = make_service_with_model(
        make_segment(" Hello world"),
        make_segment(" This is a test"),
    )
    result = await svc.transcribe(Path("/fake/audio.wav"))
    assert result == "Hello world\nThis is a test"


async def test_transcribe_strips_whitespace_from_segments():
    svc = make_service_with_model(make_segment("  lots of   whitespace  "))
    result = await svc.transcribe(Path("/fake/audio.wav"))
    assert result == "lots of   whitespace"


async def test_transcribe_timestamps_format():
    svc = make_service_with_model(make_segment(" Hello", start=1.5, end=3.25))
    result = await svc.transcribe(Path("/fake/audio.wav"), timestamps=True)
    assert result == "[1.50s --> 3.25s] Hello"


async def test_transcribe_empty_audio_returns_empty_string():
    svc = make_service_with_model()
    result = await svc.transcribe(Path("/fake/audio.wav"))
    assert result == ""


async def test_transcribe_passes_language_to_model():
    svc = make_service_with_model(make_segment(" Bonjour"))
    result = await svc.transcribe(Path("/fake/audio.wav"), language="fr")
    _, call_kwargs = svc._model.transcribe.call_args
    assert call_kwargs["language"] == "fr"
    assert result == "Bonjour"
