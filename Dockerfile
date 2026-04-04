# ─────────────────────────────────────────────────────────────────────────────
# Legal AI Platform — Backend (Python / FastAPI)
# ─────────────────────────────────────────────────────────────────────────────
# This Dockerfile builds the FastAPI backend service.
# For local development use docker-compose.yml instead:
#   docker compose up --build
#
# Each service has its own Dockerfile:
#   backend/Dockerfile   — Python 3.11 + FastAPI + Alembic
#   frontend/Dockerfile  — Node 20 + Next.js 14
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-ukr \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "echo 'Starting container...' && echo 'Running migrations...' && alembic upgrade head && echo 'Migrations done, starting server...' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
