"""Tests for DiarizationService."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.diarization import DiarizationService


def make_turn(start: float, end: float) -> MagicMock:
    """Build a mock pyannote turn object."""
    turn = MagicMock()
    turn.start = start
    turn.end = end
    return turn


def make_service_with_pipeline(tracks: list) -> DiarizationService:
    """Return a DiarizationService whose pipeline returns the given tracks."""
    svc = DiarizationService()
    mock_annotation = MagicMock()
    mock_annotation.itertracks.return_value = tracks
    # pyannote 4.x DiarizeOutput uses .speaker_diarization
    mock_output = MagicMock(spec=["speaker_diarization"])
    mock_output.speaker_diarization = mock_annotation
    mock_pipeline = MagicMock(return_value=mock_output)
    svc._pipeline = mock_pipeline
    return svc


def test_is_loaded_before_pipeline_load():
    svc = DiarizationService()
    assert svc.is_loaded is False


def test_is_loaded_after_pipeline_load():
    svc = DiarizationService()
    with (
        patch("app.services.diarization.settings") as mock_settings,
        patch("pyannote.audio.Pipeline") as mock_pipeline_cls,
    ):
        mock_settings.hf_token = "fake-token"
        mock_pipeline_cls.from_pretrained.return_value = MagicMock()
        svc._load_pipeline()
    assert svc.is_loaded is True


def test_load_pipeline_raises_without_hf_token():
    svc = DiarizationService()
    with patch("app.services.diarization.settings") as mock_settings:
        mock_settings.hf_token = None
        with pytest.raises(RuntimeError, match="HF_TOKEN is required"):
            svc._load_pipeline()


def test_run_diarization_returns_segment_list():
    tracks = [
        (make_turn(0.0, 2.0), None, "SPEAKER_00"),
        (make_turn(2.5, 5.0), None, "SPEAKER_01"),
    ]
    svc = make_service_with_pipeline(tracks)
    result = svc._run_diarization(Path("/fake/audio.wav"))
    assert result == [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        {"start": 2.5, "end": 5.0, "speaker": "SPEAKER_01"},
    ]


def test_run_diarization_empty_returns_empty_list():
    svc = make_service_with_pipeline([])
    result = svc._run_diarization(Path("/fake/audio.wav"))
    assert result == []


async def test_diarize_returns_segments():
    tracks = [(make_turn(0.0, 1.0), None, "SPEAKER_00")]
    svc = make_service_with_pipeline(tracks)
    result = await svc.diarize(Path("/fake/audio.wav"))
    assert result == [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
