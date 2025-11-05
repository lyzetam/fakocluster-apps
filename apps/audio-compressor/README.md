# Audio Compressor

Nightly batch processing service that downloads audio files from an SFTP server, compresses them using FFmpeg, and stores them in a persistent volume (PVC).

## Features

- 🔄 **SFTP Integration**: Connects to SFTP server running on Kubernetes
- 🗜️ **Audio Compression**: Uses FFmpeg to compress audio files (16kHz, mono, 32kbps)
- 💾 **Persistent Storage**: Saves compressed files to PVC with flat directory structure
- 📊 **Manifest Tracking**: Maintains JSON manifest with processing history and statistics
- ⚙️ **Configuration-Driven**: All settings via environment variables
- 🔐 **AWS Secrets Manager**: Secure credential management
- 🔁 **Smart Processing**: Skips already processed files
- 📝 **Comprehensive Logging**: Detailed logging with structured output
- 🎯 **Error Handling**: Robust retry logic and graceful error handling

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
```
PVC: /data/compressed/
├── 10-17-25_compressed.wav
├── 10-17-25-01_compressed.wav
├── 10-17-25-02_compressed.wav
├── 10-17-25_meta.xml (optional)
├── 10-17-25-01_meta.xml (optional)
└── manifest.json
```

## Configuration

All configuration is done via environment variables:

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `SFTP_HOST` | SFTP server hostname | `sftp-service.default.svc.cluster.local` |
| `SFTP_PORT` | SFTP server port | `22` |
| `SFTP_REMOTE_PATH` | Base path on SFTP server | `/audio` |
| `OUTPUT_DIR` | Output directory (PVC mount) | `/data/compressed` |

### Credentials

Credentials are loaded from AWS Secrets Manager or environment variables:

**AWS Secrets Manager** (preferred):
- Secret name: Configured via `SFTP_SECRETS_NAME`
- Secret format: JSON with `username` and `password` keys

**Environment Variables** (fallback):
- `SFTP_USERNAME`: SFTP username
- `SFTP_PASSWORD`: SFTP password

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region for Secrets Manager |
| `SFTP_SECRETS_NAME` | `sftp/audio-server` | AWS Secrets Manager secret name |
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
3. **Scan**: List all directories matching pattern (e.g., `10-17-25`, `10-17-25-01`)
4. **Process Each Directory**:
   - Check if already processed (skip if `SKIP_PROCESSED=true`)
   - Download `StereoMix.wav` to temp directory
   - Compress with FFmpeg: `ffmpeg -i input.wav -ar 16000 -ac 1 -b:a 32k output.wav`
   - Save compressed file to PVC: `/data/compressed/{dirname}_compressed.wav`
   - Optionally copy `Meta.xml` to PVC
   - Update manifest with results
   - Clean up temp files
5. **Summary**: Generate processing report with statistics

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

The service maintains a `manifest.json` file in the output directory:

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
      "status": "success"
    }
  ]
}
```

## Exit Codes

- `0`: Success - all directories processed successfully
- `1`: Partial failure - some directories failed
- `2`: Total failure - configuration error, SFTP connection failed, or all directories failed
- `130`: Interrupted by user (Ctrl+C)

## Development

### Local Testing

1. Set up environment variables:
```bash
export SFTP_HOST=your-sftp-host
export SFTP_USERNAME=your-username
export SFTP_PASSWORD=your-password
export SFTP_REMOTE_PATH=/audio
export OUTPUT_DIR=/tmp/compressed
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
- Check logs for specific errors

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
