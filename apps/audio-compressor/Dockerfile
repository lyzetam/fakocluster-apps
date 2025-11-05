FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# - ffmpeg: for audio compression
# - openssh-client: for SFTP connections
# - libpq-dev gcc: for AWS SDK and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    openssh-client \
    libpq-dev \
    gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /data/compressed && \
    mkdir -p /tmp/audio-processing && \
    chmod 755 /data && \
    chmod 755 /tmp/audio-processing

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application code
COPY externalconnections/ ./externalconnections/
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app

# Default environment variables
ENV OUTPUT_DIR=/data/compressed
ENV TEMP_DIR=/tmp/audio-processing
ENV AWS_DEFAULT_REGION=us-east-1
ENV LOG_LEVEL=INFO
ENV SKIP_PROCESSED=true
ENV COPY_METADATA=true
ENV SAMPLE_RATE=16000
ENV CHANNELS=1
ENV BITRATE=32k

# Run as non-root user for security
RUN useradd -m -u 1000 audiouser && \
    chown -R audiouser:audiouser /app /data /tmp/audio-processing
USER audiouser

# Run the audio compressor
CMD ["python", "-u", "-m", "src.main"]
