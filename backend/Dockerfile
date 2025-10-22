# Multi-stage Dockerfile for VigilantEye Backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    libgfortran5 \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/core.txt && \
    pip install --no-cache-dir -r requirements/ai_services.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/videos storage/evidence storage/model_cache storage/vector_db logs

# Set permissions
RUN chmod -R 755 storage logs

# Create non-root user
RUN groupadd -r vigilanteye && useradd -r -g vigilanteye vigilanteye
RUN chown -R vigilanteye:vigilanteye /app
USER vigilanteye

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
