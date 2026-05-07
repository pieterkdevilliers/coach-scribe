"""Speaker diarization service using pyannote.audio."""
import asyncio
import logging
import threading
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class DiarizationService:
    """Wraps pyannote speaker-diarization-3.1. Pipeline loaded lazily."""

    def __init__(self) -> None:
        """Initialise with no pipeline; built lazily on first diarize call."""
        self._pipeline = None
        self._lock = threading.Lock()

    def _load_pipeline(self) -> None:
        """Thread-safe lazy initialisation of the pyannote pipeline."""
        with self._lock:
            if self._pipeline is not None:
                return
            if not settings.hf_token:
                raise RuntimeError(
                    "HF_TOKEN is required for speaker diarization. "
                    "Set it in .env and accept the pyannote model terms at "
                    "huggingface.co/pyannote/speaker-diarization-3.1"
                )
            from pyannote.audio import Pipeline

            logger.info("Loading pyannote speaker diarization pipeline")
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=settings.hf_token,
            )

    def _run_diarization(self, file_path: Path) -> list[dict]:
        """Blocking diarization call; always invoked via asyncio.to_thread."""
        self._load_pipeline()
        logger.info("Running diarization on %s", file_path.name)
        output = self._pipeline(str(file_path))
        # Resolve the Annotation from whichever wrapper pyannote returns.
        # pyannote 4.x DiarizeOutput uses .speaker_diarization; older versions
        # returned an Annotation directly (has .itertracks).
        if hasattr(output, "itertracks"):
            annotation = output
        elif hasattr(output, "speaker_diarization"):
            annotation = output.speaker_diarization
        elif isinstance(output, dict) and "diarization" in output:
            annotation = output["diarization"]
        elif hasattr(output, "diarization"):
            annotation = output.diarization
        else:
            public_attrs = [a for a in dir(output) if not a.startswith("_")]
            raise RuntimeError(
                f"Unsupported pyannote output type '{type(output).__name__}'. "
                f"Public attributes: {public_attrs}"
            )
        return [
            {"start": turn.start, "end": turn.end, "speaker": speaker}
            for turn, _, speaker in annotation.itertracks(yield_label=True)
        ]

    async def diarize(self, file_path: Path) -> list[dict]:
        """Return speaker segments as [{start, end, speaker}, ...]."""
        return await asyncio.to_thread(self._run_diarization, file_path)

    @property
    def is_loaded(self) -> bool:
        """True once the pyannote pipeline has been loaded into memory."""
        return self._pipeline is not None


diarization_service = DiarizationService()
