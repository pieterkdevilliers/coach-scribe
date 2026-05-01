## Tech Stack
- **Backend**: Use FastAPI (Python) for API development. Rely on Pydantic for data validation, models, and type hints. Avoid other frameworks like Flask or Django.
- **Frontend**: Use VueJS with Nuxt for UI and server-side rendering. Stick to Vue Composition API and Pinia for state management. Do not use React, Angular, or other alternatives.

## Python Environment & Package Management
- **Use uv exclusively** for all Python-related tasks in this project.
- **Never** use pip, venv, virtualenv, poetry, conda, or requirements.txt directly.
- Manage dependencies via `pyproject.toml` + `uv.lock`.
- Create and activate virtual environments implicitly with uv commands.
- Key uv commands to prefer:
  - `uv add <package>` — to add dependencies (automatically updates pyproject.toml and uv.lock)
  - `uv add --dev <package>` — for development/test tools (e.g., pytest, ruff)
  - `uv sync` — to install/sync all dependencies from uv.lock
  - `uv run <command>` — to run scripts, tests, or the app inside the project environment (e.g., `uv run python -m myapp`, `uv run pytest`, `uv run fastapi dev main.py`)
  - `uv run --with <package> <command>` — for one-off tools without permanent installation
  - `uv tool install <tool>` — for globally available CLI tools if needed (rare in this project)
- When suggesting or executing installation steps, always write them as uv commands.
- When running the FastAPI app, prefer: `uv run fastapi dev app/main.py` (or your entry point).
- For scripts/tests/linters: always wrap with `uv run` (e.g., `uv run ruff check .`, `uv run pytest`).

## Architecture Decisions
- **Backend**: Organize routes by feature in FastAPI. Use dependency injection for services. All data models must use Pydantic v2. Async/await for I/O-bound operations.
- **Frontend**: Pages in `pages/` directory via Nuxt. Components in `components/`. API calls handled with `useFetch` or composables. No direct DOM manipulation—use Vue directives.

## Coding Standards
- Follow PEP 8 for Python; Airbnb style for JavaScript/TypeScript.
- Use `snake_case` in backend, `camelCase` in frontend.
- Always include type hints and tests (e.g., pytest for backend).
- Use modern Python packaging standards: `pyproject.toml` for configuration, uv for resolution/installation/locking.

## Preferred Libraries & Tools
- **Backend**: FastAPI, Pydantic (v2+), (optionally SQLAlchemy/others if needed — add via uv add).
- **Development tools**: ruff (linter/formatter), pytest (testing) — install as dev dependencies with `uv add --dev`.
- **Do not** suggest or use pip install, python -m venv, or legacy requirements files.

## Additional Guidelines
- If the project does not yet have pyproject.toml or uv.lock, initialize with `uv init` (or suggest the user run it).
- When adding new features or fixes that require new packages, explicitly propose the `uv add` command and wait for confirmation before proceeding.
- Reminder: All Python execution in this project should happen via `uv run` to ensure the correct locked environment is used.