FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ \
    ffmpeg \
    libsm6 libxext6 libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/videos storage/evidence models logs

EXPOSE 5000

# HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
#   CMD python -c "import requests; requests.get('http://localhost:5000/api/health/status')"

CMD ["python", "run.py"]

# Production optimization tips:
# - Use a multi-stage build to reduce final image size
# - Replace the Flask dev server with gunicorn:
#   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
# - Set FLASK_ENV=production and configure logging accordingly

