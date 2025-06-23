FROM python:3.11-slim

WORKDIR /app

# Create data directory
RUN mkdir -p /data && chmod 755 /data

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/data') else 1)"

# Run collector
CMD ["python", "-u", "src/collector/collector.py"]