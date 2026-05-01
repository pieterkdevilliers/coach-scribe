# Scribe API — CLAUDE.md

## Project Overview
Scribe API is a self-contained, fully local audio/video transcription and extraction service.
It runs as a Docker container on a CPU-only Linux server. No external API calls are made during
processing — all transcription and LLM inference runs locally.

This service is intentionally generic. It has no concept of "call types", users, or business logic.
It receives a file and a prompt, and returns a transcript and/or structured extraction. All
business logic lives in the Coach App (a separate service).

---

## Tech Stack
- **Runtime:** Python 3.12
- **Framework:** FastAPI — do not use Flask, Django, or any other framework
- **Validation:** Pydantic v2 for all data models and type hints
- **Transcription:** faster-whisper (local, CPU mode)
- **LLM Runtime:** Ollama (local, CPU mode)
- **LLM Model:** llama3.1:8b (Q4 quantised) — optimised for instruction-following on CPU
- **AI Orchestration:** Pydantic-AI (for structured LLM extraction)
- **Job Queue:** ARQ (async job queue, Redis-backed)
- **Redis:** Job queue broker and result store
- **Containerisation:** Docker + Docker Compose

---

## Python Environment & Package Management
- **Use uv exclusively** for all Python-related tasks in this project.
- **Never** use pip, venv, virtualenv, poetry, conda, or requirements.txt directly.
- Manage dependencies via `pyproject.toml` + `uv.lock`.
- Key uv commands to prefer:
  - `uv add <package>` — to add dependencies (automatically updates pyproject.toml and uv.lock)
  - `uv add --dev <package>` — for development/test tools (e.g., pytest, ruff)
  - `uv sync` — to install/sync all dependencies from uv.lock
  - `uv run <command>` — to run scripts, tests, or the app inside the project environment
  - `uv run fastapi dev app/main.py` — to run the FastAPI app in development
  - `uv run --with <package> <command>` — for one-off tools without permanent installation
- When suggesting or executing installation steps, always write them as uv commands.
- For scripts/tests/linters: always wrap with `uv run` (e.g., `uv run ruff check .`, `uv run pytest`).
- If the project does not yet have pyproject.toml or uv.lock, initialise with `uv init`.
- When adding new packages, explicitly propose the `uv add` command and wait for confirmation.

---

## Key Design Principles
- **Stateless:** This service stores nothing permanently. Uploaded files are written to a temp
  directory, processed, and deleted. Results are returned to the caller or polled via job ID.
- **Async-first:** All processing jobs are queued via ARQ. Endpoints return a job_id immediately.
  Callers poll GET /job/{id} for results. This is essential — CPU transcription of a 90-minute
  file can take 20–45 minutes.
- **Generic:** Never add business-domain logic here. The prompt is always supplied by the caller.
- **Accuracy over speed:** Model and Whisper settings should favour accuracy. The caller has
  already accepted that processing is slow.

---

## Architecture
- Organise routes by feature in FastAPI
- Use dependency injection for services
- All data models must use Pydantic v2
- Use `async def` and `await` for all I/O-bound operations — no blocking calls on the main thread
- Follow PEP 8 for all Python code
- Use `snake_case` throughout

---

## Project Structure
```
scribe-api/
├── app/
│   ├── main.py              # FastAPI app, route registration
│   ├── api/
│   │   ├── routes/
│   │   │   ├── process.py   # POST /transcribe, /extract, /process
│   │   │   └── jobs.py      # GET /job/{id}, GET /health
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── queue.py         # ARQ worker and queue setup
│   │   └── temp_files.py    # Temp file handling and cleanup
│   ├── services/
│   │   ├── transcription.py # faster-whisper wrapper
│   │   └── extraction.py    # Pydantic-AI + Ollama extraction
│   └── schemas/
│       ├── jobs.py          # JobStatus, JobResult Pydantic models
│       └── requests.py      # Request/response Pydantic models
├── worker.py                # ARQ worker entrypoint
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # All dependencies and config managed here
├── uv.lock
└── .env.example
```

---

## API Endpoints

### POST /transcribe
Accepts a multipart audio or video file. Queues a transcription job.
Returns: `{ job_id: str }`

### POST /extract
Accepts a JSON body with `transcript: str` and `prompt: str`.
Queues an LLM extraction job.
Returns: `{ job_id: str }`

### POST /process
Convenience endpoint. Accepts a multipart file plus a `prompt` form field.
Queues a combined transcription + extraction job.
Returns: `{ job_id: str }`

### GET /job/{id}
Poll for job result.
Returns: `{ job_id, status: pending|processing|complete|failed, result?: {...}, error?: str }`

### GET /health
Returns service health, queue depth, and Ollama/Whisper availability.

---

## Schemas (Pydantic v2)

```python
class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"

class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    transcript: str | None = None
    extraction: dict | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

class ProcessRequest(BaseModel):
    prompt: str  # Supplied by caller — no defaults here

class ExtractRequest(BaseModel):
    transcript: str
    prompt: str
```

---

## Transcription Service (faster-whisper)
- Model size: `medium` (good accuracy/speed balance on CPU)
- Language: default to `en`, accept override in request
- Use `beam_size=5` for accuracy
- VAD filter enabled to skip silence
- Output: plain text transcript (no timestamps needed by default, but accept a flag)

## Extraction Service (Pydantic-AI + Ollama)
- Ollama base URL: configurable via `OLLAMA_BASE_URL` env var (default: `http://ollama:11434`)
- Model: configurable via `LLM_MODEL` env var (default: `llama3.1:8b`)
- Pydantic-AI agent should accept a free-form prompt and return structured JSON
- The caller defines the schema via the prompt — the service returns a `dict`
- Always include the full transcript in the LLM context

---

## Preferred Libraries & Tools
- **Core:** FastAPI, Pydantic v2, pydantic-settings, pydantic-ai, faster-whisper, ARQ, httpx
- **Dev tools:** ruff (linter/formatter), pytest — install as dev dependencies via `uv add --dev`
- **Do not** suggest or use pip install, python -m venv, or legacy requirements files

---

## Environment Variables (.env)
```
REDIS_URL=redis://redis:6379
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b
WHISPER_MODEL=medium
TEMP_DIR=/tmp/scribe
MAX_FILE_SIZE_MB=500
```

---

## Docker Compose Services
- `scribe-api` — FastAPI app (port 8000)
- `worker` — ARQ worker (same image, different entrypoint)
- `redis` — ARQ broker and result store
- `ollama` — Local LLM runtime (pull model on first start)

---

## Conventions
- Use `pydantic-settings` for all config — no raw `os.environ` calls
- All endpoints return consistent JSON — never return plain text
- Log job_id at every stage for traceability
- Temp files must always be cleaned up in a `finally` block — never leak files
- Wrap all Ollama and Whisper calls in try/except and surface errors clearly in job result
- Always include type hints on all functions and methods
- Always include tests (pytest) for new features — run via `uv run pytest`
