"""LLM extraction service using pydantic-ai backed by a local Ollama instance."""
import asyncio
import logging

from json_repair import repair_json

from app.core.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a data extraction assistant. "
    "You MUST respond with a valid JSON object only. "
    "Your entire response must start with '{' and end with '}'. "
    "No markdown, no explanation, no code fences — raw JSON only."
)


class ExtractionService:
    """Pydantic-AI agent backed by a local Ollama instance."""

    def __init__(self) -> None:
        """Initialise with no agent; built lazily on first extract call."""
        self._agent = None
        self._lock: asyncio.Lock | None = None

    async def _ensure_agent(self) -> None:
        """Build the pydantic-ai Agent if not already initialised."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._agent is not None:
                return
            from pydantic_ai import Agent
            from pydantic_ai.models.openai import OpenAIModel
            from pydantic_ai.providers.ollama import OllamaProvider

            model = OpenAIModel(
                settings.llm_model,
                provider=OllamaProvider(base_url=f"{settings.ollama_base_url}/v1"),
            )
            self._agent = Agent(
                model,
                output_type=str,
                system_prompt=_SYSTEM_PROMPT,
            )
            logger.info(
                "ExtractionService agent built: %s @ %s",
                settings.llm_model,
                settings.ollama_base_url,
            )

    async def extract(self, transcript: str, prompt: str) -> dict:
        """Run LLM extraction against the transcript. Returns parsed JSON dict."""
        await self._ensure_agent()

        user_message = (
            f"TRANSCRIPT:\n{transcript}\n\n"
            f"INSTRUCTION:\n{prompt}\n\n"
            "IMPORTANT: Your response must be a JSON object only. "
            "Start with '{' and end with '}'."
        )
        logger.info("Running extraction with model %s", settings.llm_model)

        result = await self._agent.run(
            user_message,
            model_settings={"timeout": settings.llm_timeout},
        )
        raw = result.output.strip()

        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]).rsplit("```", 1)[0].strip()

        repaired = repair_json(raw, return_objects=True)
        if isinstance(repaired, dict):
            return repaired

        # Model returned plain text despite instructions — wrap it so the job
        # completes rather than fails, and the caller can see the raw output.
        logger.warning("Model returned non-JSON output; wrapping as plain text.")
        return {"result": raw}

    @property
    def is_ready(self) -> bool:
        """True once the agent has been built."""
        return self._agent is not None


extraction_service = ExtractionService()
