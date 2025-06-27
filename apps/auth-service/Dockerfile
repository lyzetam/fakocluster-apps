FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application code - paths relative to build context (./apps/auth-service)
COPY externalconnections/ ./externalconnections/
COPY src/ ./src/

# Set Python path - must include /app for imports to work
ENV PYTHONPATH=/app

# Default environment variables
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV HEALTH_CHECK_PORT=8080

# Create non-root user
RUN useradd -m -u 1000 authservice && \
    chown -R authservice:authservice /app

USER authservice

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["python", "-m", "src.auth.app"]