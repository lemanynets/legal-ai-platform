# Build context must be the project root (docker-compose: context: .)
FROM python:3.12-slim

# System deps for LibreOffice (PDF rendering) + asyncpg build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Install Python deps first (layer cache)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend package (app/db.py, app/models/, app/services/) + entry point
COPY backend/app/ ./app/
COPY backend/main.py ./

# Copy frontend source so analyze/ module is importable
COPY frontend/ ./frontend/

# Both /srv (backend package root) and /srv/frontend are on the path
ENV PYTHONPATH="/srv:/srv/frontend"
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
