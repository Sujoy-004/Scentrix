# Scentrix API - runtime image.
#
# Build context is the REPOSITORY ROOT (not backend/):
#   docker build -f backend/Dockerfile -t scentrix-api .
#
# Runtime dependencies only. The training stack (torch, sentence-transformers)
# lives in the "ml" extra of pyproject.toml and is NOT installed here - it
# pulls in ~2.5 GB and is only needed to regenerate the embeddings.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl is used by the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first so the layer is reused while app code changes.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Application code and the serving artifacts (catalog JSON + embeddings).
COPY backend/app ./app

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The API reports itself healthy even when the database is unreachable - the
# catalog and the recommender are file-backed and keep working.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Koyeb and most PaaS providers inject the port; 8000 is the local default.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
