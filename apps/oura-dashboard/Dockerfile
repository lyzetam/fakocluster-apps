FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application files - paths relative to build context (./apps/oura-dashboard)
COPY externalconnections/ ./externalconnections/
COPY src/ ./src/

# Create .streamlit directory and copy config
RUN mkdir -p /root/.streamlit
COPY streamlit_config.toml /root/.streamlit/config.toml

# Set Python path - must include /app for externalconnections to be found
# ENV PYTHONPATH=/app
ENV PYTHONPATH=/app:/app/src

# Default environment variables
ENV STORAGE_BACKEND=postgres
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO
ENV USE_AWS_SECRETS=true

# Streamlit specific
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create non-root user
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app && \
    mkdir -p /home/streamlit/.streamlit && \
    cp /root/.streamlit/config.toml /home/streamlit/.streamlit/config.toml && \
    chown -R streamlit:streamlit /home/streamlit/.streamlit

USER streamlit

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.address", "0.0.0.0"]