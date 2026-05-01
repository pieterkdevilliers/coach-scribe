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

    def _run_transcription(
        self, file_path: Path, language: str, timestamps: bool
    ) -> str:
        """Blocking transcription call; always invoked via asyncio.to_thread."""
        self._load_model()

        segments, _info = self._model.transcribe(
            str(file_path),
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        if timestamps:
            lines = [
                f"[{seg.start:.2f}s --> {seg.end:.2f}s] {seg.text.strip()}"
                for seg in segments
            ]
        else:
            lines = [seg.text.strip() for seg in segments]

        return "\n".join(lines)

    async def transcribe(
        self,
        file_path: Path,
        language: str = "en",
        timestamps: bool = False,
    ) -> str:
        """Transcribe audio/video file; returns plain text or timestamped lines."""
        logger.info("Transcribing %s (language=%s)", file_path.name, language)
        return await asyncio.to_thread(
            self._run_transcription, file_path, language, timestamps
        )

    @property
    def is_loaded(self) -> bool:
        """True once the Whisper model has been loaded into memory."""
        return self._model is not None


transcription_service = TranscriptionService()
