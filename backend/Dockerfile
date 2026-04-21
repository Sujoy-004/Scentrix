FROM python:3.11-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Create non-root user
RUN useradd -m -u 1000 appuser
# Copy pyproject and code for dependency installation
COPY backend/pyproject.toml .
COPY backend/README.md .
COPY backend/app app

# Install project dependencies
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir ".[runtime]"

# Copy ML components and additional configs
COPY ml/data ml/data
COPY ml/graph ml/graph
COPY ml/__init__.py ml/__init__.py
COPY backend/alembic.ini .
COPY backend/Procfile .



# Change ownership
RUN chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app

# Expose port (metadata)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=300s --timeout=15s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
