
# yt-analytics-fastapi-starter

Minimal FastAPI backend skeleton for YouTube data analytics.
- FastAPI + Uvicorn
- Async SQLAlchemy (Postgres) + Alembic
- Redis cache
- Docker Compose for dev/prod
- Pydantic Settings for config
- Pre-commit: ruff, mypy, pytest

## Quickstart (with uv)
```bash
# 1) Install uv (macOS)
# curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip install --upgrade pip

# 2) Install deps
uv add fastapi uvicorn[standard] httpx pydantic-settings redis sqlalchemy[asyncio] asyncpg alembic polars tenacity aiolimiter apscheduler python-dotenv

uv add --dev pytest pytest-asyncio httpx ruff mypy pre-commit

# 3) Copy env and edit values
cp .env.example .env

# 4) Run API (local, without docker)
uv run uvicorn app.main:app --reload --port 8080

# 5) Or run with Docker (dev)
docker compose -f infra/docker-compose.dev.yml up --build
```

## Endpoints
- GET `/healthz`
- GET `/api/live/top` (stub)
- GET `/api/search/summary` (stub)
