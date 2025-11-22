FROM python:3.11-slim

WORKDIR /app

# Install dependencies
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
