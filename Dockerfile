# ==============================================================
# Stage 1: Build the React 18 Frontend
# ==============================================================
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================
# Stage 2: Python 3.11 Stateless Production Runtime
# ==============================================================
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for deterministic dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python backend dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend application code and static knowledge corpus
COPY corpus/ ./corpus/
COPY agents/ ./agents/
COPY tools/ ./tools/

# Ensure runtime directories exist
RUN mkdir -p corpus/data corpus/director_output .cache/user_uploads output/renders

# Copy compiled frontend SPA from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn tools.studio_api:app --host 0.0.0.0 --port ${PORT}"]

