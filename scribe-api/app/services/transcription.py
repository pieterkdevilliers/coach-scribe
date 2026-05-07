"""Transcription service using faster-whisper, with optional speaker diarization."""
import asyncio
import logging
import threading
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Wraps faster-whisper. Model loaded lazily and reused across jobs."""

    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()

    def _load_model(self) -> None:
        """Thread-safe lazy initialisation of the Whisper model."""
        with self._lock:
            if self._model is not None:
                return
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper model: %s", settings.whisper_model)
            self._model = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )

    def _run_transcription_raw(self, file_path: Path, language: str) -> list:
        """Blocking transcription call; returns consumed segment list."""
        self._load_model()
        segments_iter, _info = self._model.transcribe(
            str(file_path),
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        return list(segments_iter)

    def _format_segments(self, segments: list, timestamps: bool) -> str:
        """Format raw segment list to plain text or timestamped lines."""
        if timestamps:
            lines = [
                f"[{seg.start:.2f}s --> {seg.end:.2f}s] {seg.text.strip()}"
                for seg in segments
            ]
        else:
            lines = [seg.text.strip() for seg in segments]
        return "\n".join(lines)

    def _merge_with_speakers(
        self, segments: list, diarization: list[dict]
    ) -> str:
        """Align Whisper segments with pyannote speaker labels."""
        lines: list[str] = []
        current_speaker: str | None = None
        current_texts: list[str] = []

        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue

            speaker_times: dict[str, float] = {}
            for d in diarization:
                overlap = max(
                    0.0, min(seg.end, d["end"]) - max(seg.start, d["start"])
                )
                if overlap > 0:
                    speaker_times[d["speaker"]] = (
                        speaker_times.get(d["speaker"], 0.0) + overlap
                    )

            speaker = (
                max(speaker_times, key=speaker_times.get)
                if speaker_times
                else "UNKNOWN"
            )

            if speaker != current_speaker:
                if current_texts and current_speaker is not None:
                    lines.append(
                        f"{current_speaker}: {' '.join(current_texts)}"
                    )
                current_speaker = speaker
                current_texts = [text]
            else:
                current_texts.append(text)

        if current_texts and current_speaker is not None:
            lines.append(f"{current_speaker}: {' '.join(current_texts)}")

        return "\n\n".join(lines)

    async def transcribe(
        self,
        file_path: Path,
        language: str = "en",
        timestamps: bool = False,
        diarize: bool = False,
    ) -> str:
        """Transcribe audio/video file; returns plain text or timestamped lines."""
        logger.info(
            "Transcribing %s (language=%s, diarize=%s)",
            file_path.name,
            language,
            diarize,
        )
        segments = await asyncio.to_thread(
            self._run_transcription_raw, file_path, language
        )

        if diarize:
            from app.services.diarization import diarization_service

            diar_segments = await diarization_service.diarize(file_path)
            return self._merge_with_speakers(segments, diar_segments)

        return self._format_segments(segments, timestamps)

    @property
    def is_loaded(self) -> bool:
        """True once the Whisper model has been loaded into memory."""
        return self._model is not None


transcription_service = TranscriptionService()
