# Daily Tasks — Full-Stack Starter

A production-ready monorepo starter for full-stack web apps built with **FastAPI** (Python) and **Nuxt 3** (Vue). Ships with async SQLite via SQLAlchemy + Alembic migrations, Pinia state management, multi-stage Docker builds, and a dev environment with hot reload.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Data validation | [Pydantic v2](https://docs.pydantic.dev/latest/) |
| ORM | [SQLAlchemy 2 (async)](https://docs.sqlalchemy.org/en/20/) |
| Database | SQLite via `aiosqlite` |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) |
| Python package manager | [uv](https://docs.astral.sh/uv/) |
| Frontend framework | [Nuxt 3](https://nuxt.com/) (Vue 3, Composition API) |
| State management | [Pinia](https://pinia.vuejs.org/) |
| Linter / formatter | [Ruff](https://docs.astral.sh/ruff/) |
| Test runner | [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |
| Containers | Docker + Docker Compose |

---

## Project Structure

```
daily-tasks/
├── backend/                        # FastAPI Python service
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point + lifespan
│   │   ├── api/                    # Feature routers (add one per domain)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── services/               # Business logic + dependency injection
│   │   └── db/
│   │       ├── base.py             # DeclarativeBase (imported by all models)
│   │       └── session.py          # Async engine, session factory, get_db()
│   ├── alembic/                    # DB migrations
│   │   └── versions/               # Auto-generated migration scripts
│   ├── tests/
│   │   └── conftest.py             # Async test client + in-memory DB fixtures
│   ├── alembic.ini                 # Alembic config (DB URL, script location)
│   ├── entrypoint.sh               # Docker: runs migrations then starts server
│   ├── Dockerfile                  # Multi-stage: base → dev → production
│   ├── .dockerignore
│   └── pyproject.toml              # uv project config + tool settings
│
├── frontend/                       # Nuxt 3 frontend
│   ├── pages/                      # File-based routing
│   ├── components/                 # Reusable Vue components
│   ├── composables/                # Shared composition functions
│   ├── stores/                     # Pinia state stores
│   ├── assets/                     # Processed static assets (CSS, images)
│   ├── public/                     # Unprocessed public files
│   ├── app.vue                     # Root layout component
│   ├── nuxt.config.ts              # Nuxt config (modules, runtimeConfig, devServer)
│   ├── Dockerfile                  # Multi-stage: base → dev → build → production
│   └── .dockerignore
│
├── docker-compose.yml              # Dev orchestration (hot reload)
├── docker-compose.prod.yml         # Production orchestration
└── CLAUDE.md                       # AI assistant instructions for this project
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.9+ | [python.org](https://www.python.org/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Docker + Compose | latest | [docs.docker.com](https://docs.docker.com/get-docker/) |

---

## Getting Started

### Option A — Local Development (no Docker)

**Backend**

```bash
cd backend

# Install all dependencies (including dev)
uv sync

# Apply DB migrations
uv run alembic upgrade head

# Start the dev server (hot reload on :8000)
uv run fastapi dev app/main.py
```

**Frontend**

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server (hot reload on :3000)
npm run dev
```

### Option B — Docker Development (recommended)

```bash
# Build images and start both services with hot reload
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

Source code is volume-mounted into both containers, so edits are reflected immediately without rebuilding.

### Option C — Docker Production

```bash
docker compose -f docker-compose.prod.yml up --build
```

The frontend runs the pre-built Nuxt output (`node .output/server/index.mjs`). The backend runs uvicorn with 2 workers. Both containers restart automatically unless manually stopped.

---

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./daily_tasks.db` | SQLAlchemy async database URL |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8000` | Base URL for API calls (public, available in browser) |

Set these in a `.env` file at the project root (not committed) or directly in `docker-compose.yml`.

> **SSR + Docker note:** `NUXT_PUBLIC_API_BASE=http://backend:8000` resolves correctly for server-side (SSR) API calls via the Docker internal network. Always access the API via `useRuntimeConfig().public.apiBase` in your Vue components — Nuxt will use the env-configured value automatically.

---

## Common Commands

### Backend

```bash
# Add a runtime dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app

# Lint + format check
uv run ruff check .
uv run ruff format --check .

# Auto-fix lint issues
uv run ruff check --fix .
uv run ruff format .

# Create a new Alembic migration (after adding/changing models)
uv run alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
uv run alembic upgrade head

# Downgrade one migration
uv run alembic downgrade -1
```

### Frontend

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build locally
npm run preview

# Regenerate Nuxt types (after config changes)
npm run postinstall
```

### Docker

```bash
# Dev: start all services
docker compose up --build

# Dev: start in background
docker compose up -d --build

# Dev: view logs
docker compose logs -f

# Dev: stop and remove containers
docker compose down

# Dev: stop and remove containers + named volumes (resets DB)
docker compose down -v

# Production: start
docker compose -f docker-compose.prod.yml up --build -d

# Exec into a running container
docker compose exec backend bash
docker compose exec frontend sh
```

---

## Development Guide

### Adding a New API Feature

1. **Model** — create `backend/app/models/my_feature.py` extending `Base`
2. **Import the model** in `backend/app/models/__init__.py` so Alembic discovers it
3. **Schema** — create `backend/app/schemas/my_feature.py` with Pydantic v2 models
4. **Service** — create `backend/app/services/my_feature.py` for business logic
5. **Router** — create `backend/app/api/my_feature.py` and register it in `app/main.py`
6. **Migrate** — run `uv run alembic revision --autogenerate -m "add my_feature"`

**Example router registration in `app/main.py`:**
```python
from app.api import my_feature

app.include_router(my_feature.router, prefix="/my-feature", tags=["my-feature"])
```

### Adding a New Page (Frontend)

Create a file in `frontend/pages/`. Nuxt auto-generates routes based on the filename.

```
pages/
├── index.vue          → /
├── about.vue          → /about
└── tasks/
    ├── index.vue      → /tasks
    └── [id].vue       → /tasks/:id
```

### Adding a Pinia Store

Create a file in `frontend/stores/`:

```ts
// stores/tasks.ts
export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])

  async function fetchTasks() {
    const config = useRuntimeConfig()
    tasks.value = await $fetch(`${config.public.apiBase}/tasks`)
  }

  return { tasks, fetchTasks }
})
```

### Writing Backend Tests

Tests use an in-memory SQLite database and an async test client. Fixtures are in `backend/tests/conftest.py`.

```python
# tests/test_tasks.py
async def test_health_check(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run with:
```bash
uv run pytest -v
```

---

## Docker Architecture

### Multi-Stage Builds

Both Dockerfiles use multi-stage builds to share a common dependency-installation layer:

```
backend/Dockerfile
  base        Python 3.9-slim + uv + pyproject.toml/uv.lock
    ├─ dev        All deps (incl. dev tools), fastapi dev server
    └─ production Runtime deps only, uvicorn with 2 workers

frontend/Dockerfile
  base        Node 20-alpine + package.json
    ├─ dev        npm install + nuxt dev
    ├─ build      npm install + nuxt build
    └─ production Copies .output/ only, node server
```

### Database Persistence

The SQLite database file is stored in a Docker named volume (`backend_db` mounted at `/app/data`). This survives container restarts and `docker compose down`, but is cleared by `docker compose down -v`.

### Alembic on Startup

`backend/entrypoint.sh` runs `alembic upgrade head` before starting the server in both dev and production. This means migrations are always applied on container start with no manual step required.
