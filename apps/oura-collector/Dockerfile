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

# Copy application
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app/src:/app/src/externalconnections

# Default environment variables
ENV STORAGE_BACKEND=postgres
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, 'src'); from collector.collector import OuraCollector; print('Health check passed')"

# Run collector
CMD ["python", "-u", "src/collector/collector.py"]