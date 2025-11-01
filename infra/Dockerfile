
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=off
WORKDIR /app

# System deps (build essentials if needed)
RUN apt-get update && apt-get install -y --no-install-recommends         build-essential curl && rm -rf /var/lib/apt/lists/*

# Install uv (fast installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml /app/pyproject.toml
RUN uv pip compile --generate-hashes -q pyproject.toml -o requirements.txt && \
    uv pip install --system -r requirements.txt

FROM base AS runtime
COPY . /app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
