FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose the HTTP port
EXPOSE 8080

# Launch the monitor
CMD ["python", "-m", "src.scripts.monitor"]