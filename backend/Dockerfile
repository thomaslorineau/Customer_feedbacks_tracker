# ============================================
# VibeCoding API Server Dockerfile
# Multi-stage build for production deployment
# ============================================
FROM python:3.11-slim as builder

# Set build-time variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-docker.txt ./

# Install Python dependencies
RUN pip install --user -r requirements-docker.txt

# ============================================
# Production Stage
# ============================================
FROM python:3.11-slim

# Set runtime variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Copy and set up entrypoint script
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create directories
RUN mkdir -p /app/backups /app/logs

# Expose API port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Use entrypoint script that handles migration, then run the command
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run with Gunicorn + Uvicorn workers for production
# This provides process isolation and auto-restart on crash
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance"]
