# Audio Transcriber

Batch audio transcription service using Whisper API endpoint.

## Overview

This service scans a directory for audio files and transcribes them using a Whisper API endpoint. It's designed to run as a Kubernetes batch job, processing compressed audio files from the audio-compressor service.

## Configuration

All configuration is done via environment variables:

### Input/Output
- `INPUT_DIR` - Directory containing audio files (default: `/data/compressed`)
- `OUTPUT_DIR` - Directory to save transcriptions (default: `/data/transcriptions`)
- `AUDIO_EXTENSIONS` - Comma-separated list of extensions (default: `.mp3,.wav,.m4a,.flac,.ogg`)
- `OUTPUT_FORMAT` - Output format: `json`, `text`, `srt`, `vtt` (default: `json`)

### Whisper API (OpenAI SDK format)
- `WHISPER_BASE_URL` - Whisper API base URL (default: `http://localhost:9000/v1`)
- `WHISPER_API_KEY` - API key for authentication (**required**)
- `WHISPER_MODEL` - Model to use (default: `whisper-1`)
- `WHISPER_LANGUAGE` - Language code or `auto` (default: `auto`)
- `WHISPER_TIMEOUT` - Request timeout in seconds (default: `600`)

### Processing
- `SKIP_PROCESSED` - Skip already transcribed files (default: `true`)
- `MAX_FILE_SIZE_MB` - Skip files larger than this (default: `500`)
- `BATCH_SIZE` - Limit files per run, 0 for all (default: `0`)
- `MAX_RETRIES` - Retry attempts for failed transcriptions (default: `3`)
- `RETRY_DELAY` - Delay between retries in seconds (default: `10`)

### Logging
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Usage

### Docker

```bash
docker build -t audio-transcriber .

docker run -v /path/to/audio:/data/compressed \
           -v /path/to/output:/data/transcriptions \
           -e WHISPER_BASE_URL=http://your-whisper-server/v1 \
           -e WHISPER_API_KEY=your-api-key \
           -e WHISPER_MODEL=faster-distil-whisper-large-v3-en \
           audio-transcriber
```

### Kubernetes Deployment

#### 1. Create Secret for API Key

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: whisper-credentials
  namespace: audio-processing
type: Opaque
stringData:
  api-key: YOUR_GPUSTACK_API_KEY
```

#### 2. Create ConfigMap for Settings (Optional)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: audio-transcriber-config
  namespace: audio-processing
data:
  WHISPER_BASE_URL: "http://your-whisper-server/v1"
  WHISPER_MODEL: "faster-distil-whisper-large-v3-en"
  WHISPER_LANGUAGE: "auto"
  INPUT_DIR: "/data/compressed"
  OUTPUT_DIR: "/data/transcriptions"
  OUTPUT_FORMAT: "json"
  SKIP_PROCESSED: "true"
  MAX_FILE_SIZE_MB: "500"
  BATCH_SIZE: "0"
  LOG_LEVEL: "INFO"
```

#### 3. Create the Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: audio-transcriber
  namespace: audio-processing
spec:
  backoffLimit: 3
  template:
    spec:
      containers:
      - name: transcriber
        image: YOUR_DOCKERHUB_USERNAME/audio-transcriber:latest
        envFrom:
        - configMapRef:
            name: audio-transcriber-config
        env:
        - name: WHISPER_API_KEY
          valueFrom:
            secretKeyRef:
              name: whisper-credentials
              key: api-key
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: audio-data
      restartPolicy: OnFailure
```

#### Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WHISPER_API_KEY` | **Yes** | GPUStack API key for authentication |
| `WHISPER_BASE_URL` | Yes | Whisper API endpoint (default: `http://localhost:9000/v1`) |
| `WHISPER_MODEL` | Yes | Model name (default: `whisper-1`) |
| `INPUT_DIR` | Yes | Directory with audio files (default: `/data/compressed`) |
| `OUTPUT_DIR` | Yes | Directory for transcriptions (default: `/data/transcriptions`) |

#### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_LANGUAGE` | `auto` | Language code or `auto` for detection |
| `WHISPER_TIMEOUT` | `600` | Request timeout in seconds |
| `OUTPUT_FORMAT` | `json` | Output format: `json`, `text`, `srt`, `vtt` |
| `SKIP_PROCESSED` | `true` | Skip already transcribed files |
| `MAX_FILE_SIZE_MB` | `500` | Skip files larger than this |
| `BATCH_SIZE` | `0` | Limit files per run (0 = all) |
| `MAX_RETRIES` | `3` | Retry attempts for failures |
| `RETRY_DELAY` | `10` | Delay between retries (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

#### Apply to Cluster

```bash
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f job.yaml

# Watch progress
kubectl logs -f job/audio-transcriber -n audio-processing
```

## Output

The service creates:
- Individual transcription files (`.json`, `.txt`, `.srt`, or `.vtt`)
- A `manifest.json` with processing summary and results

### JSON Output Example

```json
{
  "text": "Hello, this is the transcribed text...",
  "_metadata": {
    "audio_file": "recording.mp3",
    "file_size_mb": 12.5,
    "model": "large-v3",
    "language": "en",
    "task": "transcribe"
  }
}
```

## Whisper Endpoints

Compatible with:
- [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice)
- [faster-whisper-server](https://github.com/fedirz/faster-whisper-server)
- Any OpenAI-compatible Whisper API
