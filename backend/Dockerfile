# ─────────────────────────────────────────────────────────────
# Build context: backend/   (Railway root directory = backend/)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Runtime deps only: libpq for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Install Python dependencies (cached layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY routers/ ./routers/
COPY main.py ./

ENV PYTHONPATH="/srv"
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
