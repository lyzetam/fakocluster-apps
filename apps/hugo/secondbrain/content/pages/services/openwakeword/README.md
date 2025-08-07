# OpenWakeWord - Wake Word Detection Service

## Overview

OpenWakeWord is a wake word detection service deployed in the Fako cluster as part of the voice assistant pipeline. It uses machine learning models to detect specific wake words (like "Hey Jarvis") in continuous audio streams. The service implements the Wyoming protocol for integration with voice assistants and can handle multiple concurrent audio streams. It's designed for low-latency, real-time wake word detection and scales automatically based on load.

## Key Features

- **Real-Time Detection**: Low-latency wake word detection
- **Multiple Models**: Support for various wake word models
- **Wyoming Protocol**: Standard voice assistant integration
- **Auto-Scaling**: HPA-based scaling for concurrent streams
- **Model Preloading**: Fast startup with preloaded models
- **High Performance**: Optimized for CPU-based inference
- **Debug Mode**: Detailed logging for troubleshooting
- **Health Monitoring**: TCP-based health checks
- **Persistent Storage**: Model caching and custom models

## Architecture

### Components

1. **Deployment**: Single to multi-replica with HPA
2. **Service**: ClusterIP on port 10400
3. **NodePort Service**: Optional external access
4. **HPA**: Auto-scaling 1-3 replicas
5. **Storage**: PVC for model storage
6. **Node Affinity**: Avoids control plane nodes

### Resource Requirements

- **Memory**: 2Gi (request), 3Gi (limit)
- **CPU**: 2 cores (request), 3 cores (limit)
- **Storage**: Persistent volume for models
- **Scaling**: Up to 3 replicas for 4+ streams

## Configuration

### Service Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| Port | `10400` | Wyoming protocol port |
| Protocol | `TCP` | Wyoming TCP transport |
| Preloaded Model | `hey_jarvis` | Default wake word |
| Debug | Enabled | Verbose logging |

### Auto-Scaling Configuration

- **Min Replicas**: 1
- **Max Replicas**: 3
- **CPU Target**: 50% utilization
- **Memory Target**: 60% utilization
- **Scale Up**: 15 seconds stabilization
- **Scale Down**: 300 seconds stabilization

## Usage

### Wyoming Protocol Access

Internal service:
```
tcp://openwakeword.openwakeword.svc.cluster.local:10400
```

Direct pod access:
```bash
# Port forward for testing
kubectl port-forward -n openwakeword svc/openwakeword 10400:10400
```

### Integration with Voice Assistants

#### Home Assistant Configuration
```yaml
wyoming:
  - name: "OpenWakeWord"
    uri: "tcp://openwakeword.openwakeword.svc.cluster.local:10400"
```

#### Python Client Example
```python
import asyncio
from wyoming.client import AsyncTcpClient

async def detect_wake_word():
    async with AsyncTcpClient("openwakeword", 10400) as client:
        # Send audio stream
        await client.write_event(...)
        # Receive detection events
        event = await client.read_event()
```

### Available Wake Words

Default models:
- `hey_jarvis` - "Hey Jarvis"
- `ok_nabu` - "OK Nabu"
- `hey_mycroft` - "Hey Mycroft"
- `alexa` - "Alexa"

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n openwakeword

# View logs
kubectl logs -n openwakeword -l app=openwakeword

# Check HPA status
kubectl get hpa -n openwakeword
```

### Adding Custom Models

1. **Download model**:
```bash
# Download .tflite model file
curl -o custom_wake_word.tflite https://example.com/model.tflite
```

2. **Copy to pod**:
```bash
POD=$(kubectl get pod -n openwakeword -l app=openwakeword -o name | head -1)
kubectl cp custom_wake_word.tflite $POD:/data/
```

3. **Update configuration**:
```bash
kubectl set env deployment/openwakeword -n openwakeword \
  PRELOAD_MODEL="hey_jarvis,custom_wake_word"
```

### Performance Tuning

Adjust detection sensitivity:
```yaml
args:
  - "--threshold"
  - "0.5"  # Lower = more sensitive
  - "--trigger-level"
  - "2"    # Consecutive detections required
```

## Troubleshooting

### No Wake Word Detection

1. **Check logs**:
```bash
kubectl logs -n openwakeword -l app=openwakeword --tail=100
```

2. **Verify audio format**:
   - Expected: 16kHz, mono, 16-bit PCM
   - Check client audio settings

3. **Test with example**:
```bash
# Send test audio
sox test.wav -t raw -r 16000 -e signed -b 16 -c 1 - | \
  nc openwakeword.openwakeword.svc.cluster.local 10400
```

### High CPU Usage

1. **Check active streams**:
```bash
kubectl logs -n openwakeword -l app=openwakeword | grep "Active streams"
```

2. **Monitor HPA**:
```bash
kubectl get hpa -n openwakeword --watch
```

3. **Adjust resources**:
```yaml
resources:
  limits:
    cpu: "4000m"  # Increase if needed
```

### Connection Issues

1. **Test TCP connectivity**:
```bash
kubectl run test-client --rm -it --image=busybox -- \
  nc -zv openwakeword.openwakeword.svc.cluster.local 10400
```

2. **Check service endpoints**:
```bash
kubectl get endpoints -n openwakeword
```

## Security Considerations

### Network Security
- Internal-only by default
- Wyoming protocol has no built-in auth
- Use NetworkPolicies to restrict access

### Resource Limits
- CPU/Memory limits prevent DoS
- HPA prevents resource exhaustion
- Node affinity for isolation

### Best Practices
1. **Isolate traffic**: Use dedicated namespace
2. **Monitor usage**: Track detection rates
3. **Update models**: Keep models current
4. **Audit access**: Log client connections
5. **Resource quotas**: Set namespace limits

## Performance Optimization

### Model Optimization

1. **Quantization**:
```python
# Reduce model size
import tensorflow as tf
converter = tf.lite.TFLiteConverter.from_saved_model(model_path)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
```

2. **Model selection**:
   - Smaller models = lower latency
   - Larger models = better accuracy

### Scaling Strategy

1. **Vertical scaling**:
   - Increase CPU for single-stream performance
   - More memory for model caching

2. **Horizontal scaling**:
   - Multiple replicas for concurrent streams
   - Load balancing via service

### Caching

Enable model caching:
```yaml
env:
  - name: MODEL_CACHE_SIZE
    value: "10"  # Cache 10 models in memory
```

## Monitoring

### Key Metrics
- Wake word detection rate
- False positive rate
- Processing latency
- Active stream count
- CPU/Memory usage per stream

### Prometheus Metrics

If enabled:
```yaml
# Example queries
rate(openwakeword_detections_total[5m])
histogram_quantile(0.95, openwakeword_latency_seconds)
```

### Logging

Important log patterns:
```bash
# Detection events
kubectl logs -n openwakeword -l app=openwakeword | grep "Detected wake word"

# Performance stats
kubectl logs -n openwakeword -l app=openwakeword | grep "Processing time"
```

## Integration Examples

### With Whisper STT

Chain with speech-to-text:
```yaml
# Voice pipeline flow
OpenWakeWord -> Whisper -> Intent Recognition -> TTS
```

### With Home Assistant

```yaml
# configuration.yaml
assist_pipeline:
  pipelines:
    - name: "Custom Assistant"
      conversation_engine: "conversation"
      stt_engine: "whisper"
      tts_engine: "piper"
      wake_word_entity: "wake_word.openwakeword"
```

### Custom Integration

```python
# Custom voice assistant
async def voice_assistant():
    wake_word = WyomingClient("openwakeword", 10400)
    stt = WyomingClient("whisper", 10300)
    
    while True:
        # Wait for wake word
        await wake_word.detect()
        # Process speech
        text = await stt.transcribe()
        # Handle command
        process_command(text)
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor detection accuracy
   - Check false positive rate
   - Review resource usage

2. **Weekly**:
   - Analyze detection patterns
   - Update model thresholds
   - Clean old logs

3. **Monthly**:
   - Update OpenWakeWord image
   - Review and add new models
   - Performance analysis

### Model Updates

```bash
# Update to latest models
kubectl exec -n openwakeword deployment/openwakeword -- \
  wget -O /data/new_model.tflite https://models.com/latest.tflite

# Restart to load new model
kubectl rollout restart deployment/openwakeword -n openwakeword
```

### Backup Models

```bash
# Backup custom models
kubectl exec -n openwakeword deployment/openwakeword -- \
  tar -czf /tmp/models.tar.gz /data/*.tflite

kubectl cp openwakeword/pod:/tmp/models.tar.gz ./openwakeword-models-backup.tar.gz
```

## Advanced Configuration

### Multi-Language Support

Configure multiple wake words:
```yaml
args:
  - "--preload-model"
  - "hey_jarvis"
  - "--preload-model"
  - "hola_jarvis"  # Spanish
  - "--preload-model"
  - "salut_jarvis"  # French
```

### Custom Thresholds

Per-model thresholds:
```yaml
env:
  - name: MODEL_hey_jarvis_THRESHOLD
    value: "0.5"
  - name: MODEL_alexa_THRESHOLD
    value: "0.7"  # Higher threshold for Alexa
```

### Audio Preprocessing

Enable noise suppression:
```yaml
args:
  - "--noise-suppression"
  - "--vad-threshold"
  - "0.5"
```

## Future Improvements

- [ ] Implement model training pipeline
- [ ] Add webhook for detection events
- [ ] Create web UI for model management
- [ ] Implement distributed detection
- [ ] Add support for custom languages
- [ ] Create A/B testing framework
- [ ] Implement detection analytics
- [ ] Add GPU acceleration support
- [ ] Create mobile SDK
- [ ] Implement edge deployment options
