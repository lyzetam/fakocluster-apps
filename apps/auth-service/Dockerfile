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
    pip install --no-cache-dir streamlit requests && \
    pip cache purge

# Copy application code - paths relative to build context (./apps/auth-service)
COPY src/externalconnections/ ./externalconnections/
COPY src/ ./src/
COPY src/ui/ ./src/ui/

# Copy Streamlit configuration
RUN mkdir -p /root/.streamlit
COPY streamlit_config.toml /root/.streamlit/config.toml

# Set Python path - must include /app for imports to work
ENV PYTHONPATH=/app

# Default environment variables
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV HEALTH_CHECK_PORT=8080
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create non-root user
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app && \
    mkdir -p /home/streamlit/.streamlit && \
    cp /root/.streamlit/config.toml /home/streamlit/.streamlit/config.toml && \
    chown -R streamlit:streamlit /home/streamlit/.streamlit

USER streamlit

# Expose ports
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "src/ui/app.py", "--server.address", "0.0.0.0"]
