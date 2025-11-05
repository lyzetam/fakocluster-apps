# Audio Compressor

Nightly batch processing service that downloads audio files from an SFTP server, compresses them using FFmpeg, and stores them in a persistent volume (PVC).

## Features

- 🔄 **SFTP Integration**: Connects to SFTP server for source audio and optional destination
- 🗜️ **Audio Compression**: Uses FFmpeg to compress audio files (16kHz, mono, 32kbps)
- 💾 **Flexible Storage**: Configuration-driven storage backends (Local PVC or SFTP)
- 🔄 **Automatic Fallback**: Falls back to local storage if SFTP upload fails
- 📊 **Manifest Tracking**: Maintains JSON manifest with processing history and statistics
- ⚙️ **Configuration-Driven**: All settings via environment variables
- 🔐 **AWS Secrets Manager**: Secure credential management
- 🔁 **Smart Processing**: Skips already processed files
- 📝 **Comprehensive Logging**: Detailed logging with structured output
- 🎯 **Error Handling**: Robust retry logic and graceful error handling
- 🔄 **Duplicate Handling**: Appends timestamps to avoid overwriting existing files

## Architecture

### Input Structure
```
SFTP Server: /audio/
├── 10-17-25/
│   ├── StereoMix.wav
│   └── Meta.xml
├── 10-17-25-01/
│   ├── StereoMix.wav
│   └── Meta.xml
└── 10-17-25-02/
    ├── StereoMix.wav
    └── Meta.xml
```

### Output Structure

**Local Storage (default):**
```
PVC: /data/compressed/
├── 10-17-25_compressed.wav
├── 10-17-25-01_compressed.wav
├── 10-17-25-02_compressed.wav
├── 10-17-25_meta.xml (optional)
├── 10-17-25-01_meta.xml (optional)
└── manifest.json
```

**SFTP Storage:**
```
SFTP Server: /compressed/
├── 10-17-25_compressed.wav
├── 10-17-25_compressed_20251104_214530.wav (duplicate with timestamp)
├── 10-17-25-01_compressed.wav
└── 10-17-25-02_compressed.wav

Local PVC (manifest always stored locally):
└── manifest.json
```

## Configuration

All configuration is done via environment variables:

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `SFTP_HOST` | SFTP server hostname (source & destination) | `sftp-service.default.svc.cluster.local` |
| `SFTP_PORT` | SFTP server port | `22` |
| `SFTP_REMOTE_PATH` | Source path on SFTP server | `/audio` |
| `OUTPUT_DIR` | Local output directory (PVC mount, also used as fallback) | `/data/compressed` |

### Credentials

Credentials are loaded from AWS Secrets Manager or environment variables:

**AWS Secrets Manager** (preferred):
- Secret name: Configured via `SFTP_SECRETS_NAME`
- Secret format: JSON with `username` and `password` keys

**Environment Variables** (fallback):
- `SFTP_USERNAME`: SFTP username
- `SFTP_PASSWORD`: SFTP password

### Storage Backend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `local` | Storage destination: `local` (PVC) or `sftp` (upload to SFTP) |
| `SFTP_DEST_PATH` | `/compressed` | Remote path on SFTP server when `STORAGE_BACKEND=sftp` |
| `UPLOAD_RETRY_ATTEMPTS` | `3` | Number of upload retry attempts for SFTP backend |
| `UPLOAD_RETRY_DELAY` | `5` | Delay between upload retries (seconds) |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region for Secrets Manager |
| `SFTP_SECRETS_NAME` | `sftp/audio-server` | AWS Secrets Manager secret name (same credentials for source & destination) |
| `SAMPLE_RATE` | `16000` | Target sample rate (Hz) |
| `CHANNELS` | `1` | Number of audio channels (1=mono) |
| `BITRATE` | `32k` | Target bitrate for compression |
| `AUDIO_FORMAT` | `wav` | Output audio format |
| `AUDIO_FILENAME` | `StereoMix.wav` | Audio filename to look for |
| `METADATA_FILENAME` | `Meta.xml` | Metadata filename to copy |
| `COPY_METADATA` | `true` | Copy metadata files |
| `SKIP_PROCESSED` | `true` | Skip already processed directories |
| `DIR_PATTERN` | `^\d{2}-\d{2}-\d{2}(-\d{2})?$` | Regex pattern for directories |
| `MAX_FILE_SIZE_MB` | `2000` | Skip files larger than this |
| `MAX_RETRIES` | `3` | Max retry attempts for downloads |
| `RETRY_DELAY` | `5` | Delay between retries (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `TEMP_DIR` | `/tmp/audio-processing` | Temporary processing directory |

## Deployment

### Docker Image

Build and push:
```bash
docker build -t yourname/audio-compressor:latest apps/audio-compressor/
docker push yourname/audio-compressor:latest
```

The image is automatically built and published to DockerHub via GitHub Actions when changes are pushed to `apps/audio-compressor/`.

### Kubernetes CronJob Example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: audio-compressor
  namespace: default
spec:
  schedule: "0 2 * * *"  # Run at 2 AM daily
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: audio-compressor
            image: yourname/audio-compressor:latest
            env:
            - name: SFTP_HOST
              value: "sftp-service.default.svc.cluster.local"
            - name: SFTP_REMOTE_PATH
              value: "/audio"
            - name: OUTPUT_DIR
              value: "/data/compressed"
            - name: AWS_DEFAULT_REGION
              value: "us-east-1"
            - name: SFTP_SECRETS_NAME
              value: "sftp/audio-server"
            - name: LOG_LEVEL
              value: "INFO"
            volumeMounts:
            - name: compressed-audio
              mountPath: /data
            resources:
              requests:
                memory: "512Mi"
                cpu: "500m"
              limits:
                memory: "2Gi"
                cpu: "2000m"
          volumes:
          - name: compressed-audio
            persistentVolumeClaim:
              claimName: audio-compressed-pvc
```

### PVC Example

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: audio-compressed-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: gp3
```

## Processing Workflow

1. **Initialize**: Load configuration and validate settings
2. **Connect**: Establish SFTP connection with credentials from AWS Secrets Manager
3. **Initialize Storage**: Create storage backend (Local or SFTP) based on `STORAGE_BACKEND` config
4. **Scan**: List all directories matching pattern (e.g., `10-17-25`, `10-17-25-01`)
5. **Process Each Directory**:
   - Check if already processed (checks SFTP destination or local storage)
   - Download `StereoMix.wav` from source SFTP to temp directory
   - Compress with FFmpeg: `ffmpeg -i input.wav -ar 16000 -ac 1 -b:a 32k output.wav`
   - Save compressed file to configured destination:
     - **Local backend**: Save to `/data/compressed/{dirname}_compressed.wav`
     - **SFTP backend**: Upload to `{SFTP_DEST_PATH}/{dirname}_compressed.wav`
       - If upload fails after retries, automatically falls back to local storage
       - If file exists, appends timestamp: `{dirname}_compressed_YYYYMMDD_HHMMSS.wav`
   - Optionally copy `Meta.xml` to same destination
   - Update manifest (always stored locally) with results and storage location
   - Clean up temp files
6. **Summary**: Generate processing report with statistics

## Compression Details

The service uses FFmpeg with the following settings optimized for speech:

- **Sample Rate**: 16kHz (Whisper's native rate)
- **Channels**: Mono (sufficient for speech)
- **Bitrate**: 32 kbps (good quality for speech)
- **Expected Reduction**: 10-20x smaller files

Example:
- Original: 156.3 MB
- Compressed: 8.2 MB
- Ratio: 19.0x

## Manifest Tracking

The service maintains a `manifest.json` file in the local output directory (regardless of storage backend):

```json
{
  "last_run": "2025-11-05T02:00:00Z",
  "total_processed": 145,
  "total_failed": 2,
  "total_space_saved_gb": 18.7,
  "directories": [
    {
      "directory": "10-17-25",
      "processed_at": "2025-11-05T02:01:23Z",
      "original_size_mb": 156.3,
      "compressed_size_mb": 8.2,
      "compression_ratio": 19.0,
      "status": "success",
      "storage_location": "sftp"
    }
  ]
}
```

The `storage_location` field indicates where the compressed file was saved: `local` or `sftp`.

## Exit Codes

- `0`: Success - all directories processed successfully
- `1`: Partial failure - some directories failed
- `2`: Total failure - configuration error, SFTP connection failed, or all directories failed
- `130`: Interrupted by user (Ctrl+C)

## Development

### Local Testing

**Example 1: Local storage (default)**
```bash
export SFTP_HOST=your-sftp-host
export SFTP_USERNAME=your-username
export SFTP_PASSWORD=your-password
export SFTP_REMOTE_PATH=/audio
export STORAGE_BACKEND=local
export OUTPUT_DIR=/tmp/compressed
export LOG_LEVEL=DEBUG
```

**Example 2: SFTP destination**
```bash
export SFTP_HOST=your-sftp-host
export SFTP_USERNAME=your-username
export SFTP_PASSWORD=your-password
export SFTP_REMOTE_PATH=/audio
export STORAGE_BACKEND=sftp
export SFTP_DEST_PATH=/compressed
export OUTPUT_DIR=/tmp/compressed  # Used as fallback
export LOG_LEVEL=DEBUG
```

2. Run locally:
```bash
cd apps/audio-compressor
python -m src.main
```

### Running with Docker

```bash
docker run -it --rm \
  -e SFTP_HOST=your-sftp-host \
  -e SFTP_USERNAME=your-username \
  -e SFTP_PASSWORD=your-password \
  -e SFTP_REMOTE_PATH=/audio \
  -e OUTPUT_DIR=/data/compressed \
  -v /path/to/local/storage:/data \
  yourname/audio-compressor:latest
```

## Monitoring

### Logs

View logs from Kubernetes:
```bash
kubectl logs -n default -l job-name=audio-compressor-xxxxx
```

### Manifest

Check processing statistics:
```bash
kubectl exec -it pod-name -- cat /data/compressed/manifest.json
```

### Storage Usage

```bash
kubectl exec -it pod-name -- du -sh /data/compressed
```

## Troubleshooting

### FFmpeg Not Found
- Ensure the Docker image includes ffmpeg (already installed in provided Dockerfile)

### SFTP Connection Failed
- Verify SFTP host and port are correct
- Check credentials in AWS Secrets Manager
- Ensure network connectivity from pod to SFTP server

### Files Not Being Processed
- Check `SKIP_PROCESSED` setting
- Verify directory pattern matches your directory names
- For SFTP backend: Check if files already exist on SFTP destination
- Check logs for specific errors

### SFTP Upload Failures
- Check network connectivity to SFTP server
- Verify `SFTP_DEST_PATH` exists or can be created
- Check SFTP server permissions
- Files will automatically fall back to local storage if upload fails
- Review manifest for `storage_location` field to see where files were saved

### Out of Space
- Monitor PVC usage
- Adjust PVC size in deployment
- Consider cleanup policies for old files

## Security

- ✅ Credentials stored in AWS Secrets Manager (never in code)
- ✅ Container runs as non-root user
- ✅ Minimal Docker image (only required packages)
- ✅ No secrets in logs or manifest

## Contributing

When making changes:
1. Update version in `src/__init__.py`
2. Test locally with sample files
3. Update this README if configuration changes
4. Push to trigger automatic Docker build

## License

Internal use only.
