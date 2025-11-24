FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg for audio chunking
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default environment variables
ENV INPUT_DIR=/data/compressed
ENV OUTPUT_DIR=/data/transcriptions
ENV WHISPER_BASE_URL=http://whisper:9000/v1
ENV WHISPER_MODEL=whisper-1
ENV WHISPER_LANGUAGE=auto
ENV LOG_LEVEL=INFO

# Run the transcription service
CMD ["python", "-m", "src.main"]
