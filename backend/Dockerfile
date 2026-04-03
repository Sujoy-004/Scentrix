FROM python:3.11-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Create non-root user
RUN useradd -m -u 1000 appuser
# Copy pyproject for dependency installation
COPY pyproject.toml .
COPY README.md .
# Install project dependencies (use built-in pip)
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir ".[ml]"
# Copy application code
COPY app app
# Change ownership
RUN chown -R appuser:appuser /app
USER appuser
# Health check
HEALTHCHECK --interval=300s --timeout=15s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
