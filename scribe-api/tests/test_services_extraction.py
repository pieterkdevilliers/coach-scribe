"""Tests for ExtractionService."""
# pylint: disable=protected-access
from unittest.mock import AsyncMock, MagicMock

from app.services.extraction import ExtractionService


def make_service_with_agent(raw_output: str) -> ExtractionService:
    """Return an ExtractionService whose agent is pre-built and returns raw_output."""
    svc = ExtractionService()
    mock_result = MagicMock()
    mock_result.output = raw_output
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)
    svc._agent = mock_agent
    return svc


def test_is_ready_before_agent_build():
    """is_ready is False before _ensure_agent has been called."""
    svc = ExtractionService()
    assert svc.is_ready is False


def test_is_ready_after_agent_set():
    """is_ready is True once _agent is populated."""
    svc = ExtractionService()
    svc._agent = MagicMock()
    assert svc.is_ready is True


async def test_extract_parses_clean_json():
    """Clean JSON output is parsed and returned as a dict."""
    svc = make_service_with_agent('{"key": "value", "count": 3}')
    result = await svc.extract("some transcript", "extract key and count")
    assert result == {"key": "value", "count": 3}


async def test_extract_repairs_stray_quote_before_closing_brace():
    """Reproduces the llama3.1:8b formatting artifact we hit in production."""
    svc = make_service_with_agent('{"summary": ["point one"]"}')
    result = await svc.extract("transcript", "summarise")
    assert isinstance(result, dict)
    assert "summary" in result


async def test_extract_strips_markdown_json_fence():
    """Markdown ```json fences are stripped before parsing."""
    svc = make_service_with_agent('```json\n{"key": "value"}\n```')
    result = await svc.extract("transcript", "extract key")
    assert result == {"key": "value"}


async def test_extract_strips_plain_code_fence():
    """Plain ``` fences are stripped before parsing."""
    svc = make_service_with_agent('```\n{"key": "value"}\n```')
    result = await svc.extract("transcript", "extract key")
    assert result == {"key": "value"}


async def test_extract_wraps_non_object_output():
    """Plain-text model output is wrapped rather than failing the job."""
    svc = make_service_with_agent('"just a plain string"')
    result = await svc.extract("transcript", "bad prompt")
    assert "result" in result
    assert isinstance(result["result"], str)


async def test_extract_passes_transcript_and_prompt_to_agent():
    """Transcript and prompt both appear in the message sent to the agent."""
    svc = make_service_with_agent('{"ok": true}')
    await svc.extract("my transcript", "my prompt")
    call_args = svc._agent.run.call_args
    user_message = call_args[0][0]
    assert "my transcript" in user_message
    assert "my prompt" in user_message
