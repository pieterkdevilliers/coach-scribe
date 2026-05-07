"""Tests for TranscriptionService."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_merge_with_speakers_groups_consecutive_same_speaker():
    svc = TranscriptionService()
    segments = [
        make_segment(" Hello there", 0.0, 1.0),
        make_segment(" How are you", 1.0, 2.0),
        make_segment(" I am fine", 2.5, 3.5),
    ]
    diarization = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        {"start": 2.5, "end": 3.5, "speaker": "SPEAKER_01"},
    ]
    result = svc._merge_with_speakers(segments, diarization)
    assert result == "SPEAKER_00: Hello there How are you\n\nSPEAKER_01: I am fine"


def test_merge_with_speakers_unknown_when_no_overlap():
    svc = TranscriptionService()
    segments = [make_segment(" Orphan text", 10.0, 11.0)]
    diarization = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = svc._merge_with_speakers(segments, diarization)
    assert result == "UNKNOWN: Orphan text"


def test_merge_with_speakers_empty_segments():
    svc = TranscriptionService()
    diar = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = svc._merge_with_speakers([], diar)
    assert result == ""


def test_merge_with_speakers_skips_empty_segment_text():
    svc = TranscriptionService()
    segments = [make_segment("   ", 0.0, 1.0), make_segment(" Hello", 1.0, 2.0)]
    diarization = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
    result = svc._merge_with_speakers(segments, diarization)
    assert result == "SPEAKER_00: Hello"


async def test_transcribe_with_diarize_calls_diarization_service():
    svc = make_service_with_model(
        make_segment(" Alice speaks", 0.0, 1.0),
        make_segment(" Bob replies", 1.5, 2.5),
    )
    mock_diar_svc = AsyncMock()
    mock_diar_svc.diarize = AsyncMock(return_value=[
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"start": 1.5, "end": 2.5, "speaker": "SPEAKER_01"},
    ])

    with patch("app.services.diarization.diarization_service", mock_diar_svc):
        result = await svc.transcribe(Path("/fake/audio.wav"), diarize=True)

    mock_diar_svc.diarize.assert_called_once()
    assert "SPEAKER_00" in result
    assert "SPEAKER_01" in result


async def test_transcribe_without_diarize_does_not_call_diarization_service():
    svc = make_service_with_model(make_segment(" Plain text"))
    mock_diar_svc = AsyncMock()

    with patch("app.services.diarization.diarization_service", mock_diar_svc):
        result = await svc.transcribe(Path("/fake/audio.wav"), diarize=False)

    mock_diar_svc.diarize.assert_not_called()
    assert result == "Plain text"
