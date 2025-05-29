FROM python:3.11-slim

# Install kubectl for metrics if enabled
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Security: Run as non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache

# Copy application code
COPY --chown=appuser:appuser src/ ./src/

# Security: Ensure templates are included but read-only
RUN chmod -R 755 /app/src && \
    chmod -R 444 /app/src/ui/templates/*

# Switch to non-root user
USER appuser

# Expose the HTTP port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health').raise_for_status()"

# Launch the monitor
CMD ["python", "-m", "src.scripts.monitor"]