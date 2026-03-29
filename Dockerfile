FROM python:3.11-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Create non-root user
RUN useradd -m -u 1000 appuser
# Copy pyproject for dependency installation
COPY backend/pyproject.toml .
COPY backend/README.md .
# Install project dependencies (use built-in pip)
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir "."
# Copy application code
COPY backend/app app
# Change ownership
RUN chown -R appuser:appuser /app
USER appuser
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
