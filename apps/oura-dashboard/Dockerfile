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

# Copy application files
COPY src/ ./src/
COPY streamlit_config.toml /root/.streamlit/config.toml

# Set Python path
ENV PYTHONPATH=/app/src

# Environment variables with defaults
ENV DATABASE_HOST=localhost
ENV DATABASE_PORT=5432
ENV DATABASE_NAME=oura_health
ENV DATABASE_USER=postgres
ENV DATABASE_PASSWORD=password
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV LOG_LEVEL=INFO

# Create non-root user
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app

USER streamlit

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.address", "0.0.0.0"]