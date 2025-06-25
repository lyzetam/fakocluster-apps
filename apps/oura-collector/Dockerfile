FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create data directory (for fallback file storage)
RUN mkdir -p /data && chmod 755 /data

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application - paths relative to build context (./apps/oura-collector)
COPY externalconnections/ ./externalconnections/
COPY src/ ./src/

# Set Python path - must include /app for externalconnections to be found
ENV PYTHONPATH=/app

# Default environment variables
ENV STORAGE_BACKEND=postgres
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO

# Health check - use wget since it's available in slim image
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run collector
CMD ["python", "-u", "src/collector/collector.py"]