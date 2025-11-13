# Stage 1: Builder (Install Dependencies)
FROM python:3.11-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements/ requirements/

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies in order (optimize caching)
# Base requirements first (core dependencies, changes less often)
RUN pip install --no-cache-dir -r requirements/base.txt

# AI services requirements (large, changes rarely)
RUN pip install --no-cache-dir -r requirements/ai_services.txt

# Stage 2: Runtime (Application)
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/storage /app/models_cache /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=src.app:create_app \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command (Gunicorn for production)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "300", \
     "--access-logfile", "-", "--error-logfile", "-", "src.app:create_app()"]

