# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
        build-essential \
            python3-dev \
                && rm -rf /var/lib/apt/lists/*

                # Upgrade pip and install torch-cpu (saves ~2GB vs default torch)
                RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
                    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

                    # Copy only dependency files
                    COPY backend/pyproject.toml .
                    COPY backend/README.md .

                    # Install dependencies into /usr/local
                    RUN pip install --no-cache-dir ".[runtime,ml]"

                    # Stage 2: Final Image
                    FROM python:3.11-slim

                    WORKDIR /app

                    # Set environment variables
                    ENV PYTHONDONTWRITEBYTECODE=1 \
                        PYTHONUNBUFFERED=1 \
                            PYTHONPATH=/app \
                                RUNNING_IN_DOCKER=true

                                # Install runtime dependencies (curl for healthcheck)
                                RUN apt-get update && apt-get install -y --no-install-recommends \
                                    curl \
                                        && rm -rf /var/lib/apt/lists/*

                                        # Copy installed packages from builder (system-wide location)
                                        COPY --from=builder /usr/local /usr/local

                                        # Copy application code
                                        COPY backend/app app/
                                        COPY ml/data/fra_elite_24k.json ml/data/
                                        COPY ml/models ml/models
                                        COPY backend/alembic.ini .
                                        COPY backend/Procfile .

                                        # Ensure all files are world-readable/executable where needed
                                        RUN chmod -R 755 /usr/local/bin

                                        # Create non-root user
                                        RUN useradd -m -u 1000 appuser && \
                                            chown -R appuser:appuser /app
                                            USER appuser

                                            EXPOSE 8000

                                            HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
                                                CMD curl -f http://localhost:8000/api/health || exit 1

                                                CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
                                                
