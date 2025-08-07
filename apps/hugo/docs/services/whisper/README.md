# Whisper Speech-to-Text Service

## Overview

Whisper is an automatic speech recognition (ASR) service deployed in the Fako cluster. It uses OpenAI's Whisper model running on GPU acceleration to provide high-quality speech-to-text transcription. The service is exposed via the Wyoming protocol, making it compatible with various voice assistant platforms.

## Key Features

- **GPU Acceleration**: Runs on NVIDIA GPU for fast transcription
- **Wyoming Protocol**: Compatible with Home Assistant and other voice platforms
- **Multiple Model Sizes**: Configurable model size (base, small, medium, large)
- **Voice Activity Detection**: Built-in VAD for efficient processing
- **Persistent Model Storage**: Models are cached to avoid re-downloading

## Architecture

### Components

1. **Deployment**: Single-replica GPU deployment pinned to the `yeezyai` node
2. **Service**: ClusterIP service on port 10300 (Wyoming protocol)
3. **Storage**: PersistentVolumeClaim for model caching
4. **ConfigMap**: Environment configuration for model parameters

### Resource Requirements

- **GPU**: 1 NVIDIA GPU (required)
- **Memory**: 2Gi (request), 4Gi (limit)
- **CPU**: 2 cores (request), 4 cores (limit)
- **Storage**: Persistent volume for model storage

## Configuration

### Model Parameters (via ConfigMap)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MODEL` | `base` | Whisper model size (tiny, base, small, medium, large) |
| `LANGUAGE` | `en` | Primary language for transcription |
| `COMPUTE_TYPE` | `float16` | GPU compute precision |
| `BEAM_SIZE` | `5` | Beam search width for decoding |

### Voice Activity Detection

| Parameter | Default | Description |
|-----------|---------|-------------|
| `VAD_THRESHOLD` | `0.5` | Voice activity detection threshold |
| `MIN_SPEECH_DURATION_MS` | `250` | Minimum speech duration in milliseconds |
| `MAX_SPEECH_DURATION_S` | `30` | Maximum speech duration in seconds |
| `SPEECH_PAD_MS` | `400` | Padding around detected speech |

## Usage

### Accessing the Service

The Whisper service is available within the cluster at:
```
whisper-gpu.whisper.svc.cluster.local:10300
```

### Wyoming Protocol Integration

The service implements the Wyoming protocol, making it compatible with:
- Home Assistant's Wyoming integration
- Rhasspy voice assistant
- Custom Wyoming protocol clients

Example Home Assistant configuration:
```yaml
wyoming:
  - name: "Whisper"
    host: whisper-gpu.whisper.svc.cluster.local
    port: 10300
```

### Testing the Service

You can test the service using a Wyoming protocol client:

```bash
# Port-forward the service for local testing
kubectl port-forward -n whisper svc/whisper-gpu 10300:10300

# Use a Wyoming client to send audio
# (Requires wyoming-cli or similar tool)
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n whisper

# View logs
kubectl logs -n whisper deployment/whisper-gpu

# Check resource usage
kubectl top pod -n whisper
```

### Changing Model Size

To use a different Whisper model:

1. Edit the ConfigMap:
```bash
kubectl edit configmap whisper-gpu-configmap -n whisper
```

2. Change the `MODEL` value to one of: `tiny`, `base`, `small`, `medium`, `large`

3. Restart the deployment:
```bash
kubectl rollout restart deployment/whisper-gpu -n whisper
```

### Model Storage

Models are stored in the persistent volume at `/data/.cache`. First-time model downloads may take several minutes depending on the model size:

- **tiny**: ~39 MB
- **base**: ~74 MB
- **small**: ~244 MB
- **medium**: ~769 MB
- **large**: ~1550 MB

## Troubleshooting

### Pod Not Starting

1. **Check GPU availability**:
```bash
kubectl describe node yeezyai | grep -A5 "Allocated resources"
```

2. **Verify GPU runtime**:
```bash
kubectl get runtimeclass nvidia
```

3. **Check pod events**:
```bash
kubectl describe pod -n whisper -l app=whisper-gpu
```

### Poor Transcription Quality

1. **Increase model size**: Larger models provide better accuracy
2. **Adjust VAD settings**: Tune the voice activity detection parameters
3. **Check audio quality**: Ensure input audio is clear and properly formatted

### High Memory Usage

1. **Monitor memory**:
```bash
kubectl top pod -n whisper
```

2. **Adjust model size**: Smaller models use less memory
3. **Check for memory leaks**: Review logs for OOM errors

## Integration Examples

### With Home Assistant

1. Add Wyoming integration
2. Configure with cluster service endpoint
3. Use in voice assistants or automations

### With Custom Applications

Python example using Wyoming protocol:
```python
import asyncio
from wyoming.client import AsyncTcpClient

async def transcribe_audio(audio_data):
    client = AsyncTcpClient('whisper-gpu.whisper.svc.cluster.local', 10300)
    await client.connect()
    result = await client.transcribe(audio_data)
    await client.disconnect()
    return result
```

## Performance Tuning

### GPU Optimization

- Ensure CUDA compatibility with the container image
- Monitor GPU utilization: `nvidia-smi`
- Consider batch processing for multiple requests

### Network Optimization

- Use NodePort service for external access if needed
- Consider service mesh for advanced routing
- Monitor network latency for real-time applications

## Security Considerations

- Service runs as non-root user (UID 1000)
- Network policies can restrict access
- Consider TLS termination for external access
- Audit transcription requests if handling sensitive data

## Monitoring

Recommended metrics to monitor:
- Pod CPU and memory usage
- GPU utilization and memory
- Request latency
- Error rates
- Model loading time

## Future Improvements

- [ ] Add Prometheus metrics endpoint
- [ ] Implement request queuing for multiple clients
- [ ] Add support for streaming transcription
- [ ] Create Grafana dashboard for monitoring
- [ ] Add multi-language model support
