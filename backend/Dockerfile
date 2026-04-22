FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    RUNNING_IN_DOCKER=true

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatchling setuptools wheel

# 1. Copy only requirements-related files for better caching
COPY backend/pyproject.toml .
COPY backend/README.md .

# 2. Install dependencies (including ML extras for production stability)
# We install [runtime,ml] to ensure all neural components work
RUN pip install --no-cache-dir ".[runtime,ml]"

# 3. Copy the rest of the application code
# Context is '.' (project root) as per railway.json
COPY backend/app app/
COPY ml/ ml/
COPY backend/alembic.ini .
COPY backend/Procfile .

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check (30s start period to allow for heavy ML model loading)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command is handled by railway.json, but we provide a robust default
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
