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

### Whisper API
- `WHISPER_ENDPOINT` - Whisper API URL (default: `http://localhost:9000/asr`)
- `WHISPER_MODEL` - Model to use (default: `base`)
- `WHISPER_LANGUAGE` - Language code (default: `en`)
- `WHISPER_TASK` - Task: `transcribe` or `translate` (default: `transcribe`)
- `WHISPER_TIMEOUT` - Request timeout in seconds (default: `600`)
- `WHISPER_WORD_TIMESTAMPS` - Enable word timestamps (default: `false`)

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
           -e WHISPER_ENDPOINT=http://whisper-server:9000/asr \
           -e WHISPER_MODEL=large-v3 \
           audio-transcriber
```

### Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: audio-transcriber
spec:
  template:
    spec:
      containers:
      - name: transcriber
        image: audio-transcriber:latest
        env:
        - name: INPUT_DIR
          value: /data/compressed
        - name: OUTPUT_DIR
          value: /data/transcriptions
        - name: WHISPER_ENDPOINT
          value: http://whisper-service:9000/asr
        - name: WHISPER_MODEL
          value: large-v3
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: audio-data
      restartPolicy: OnFailure
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
