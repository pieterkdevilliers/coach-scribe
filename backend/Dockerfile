# ---- base ----
FROM python:3.9-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# ---- dev ----
FROM base AS dev
RUN uv sync --frozen --all-groups
COPY . .
ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["uv", "run", "fastapi", "dev", "app/main.py", "--host", "0.0.0.0"]

# ---- production ----
FROM base AS production
RUN uv sync --frozen --no-dev
COPY . .
ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
