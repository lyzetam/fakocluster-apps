# Piper Text-to-Speech Service

## Overview

Piper is a fast, local text-to-speech (TTS) service deployed in the Fako cluster. It converts text into natural-sounding speech using neural voice models and exposes its functionality via the Wyoming protocol, making it compatible with voice assistant platforms like Home Assistant.

## Key Features

- **CPU-Optimized**: Runs efficiently on CPU without requiring GPU
- **Wyoming Protocol**: Compatible with Home Assistant and other voice platforms
- **Multiple Voice Support**: Various voice models with different qualities
- **Voice Management**: Automatic voice model management via sidecar container
- **Persistent Storage**: Voice models cached to avoid re-downloading
- **Scalable**: Supports multiple concurrent TTS processes

## Architecture

### Components

1. **Deployment**: Single-replica deployment with node affinity rules
2. **Service**: ClusterIP service on port 10200 (Wyoming protocol)
3. **Storage**: PersistentVolumeClaim for voice model storage
4. **ConfigMap**: Configuration for default voice settings
5. **Sidecar Container**: Voice manager for monitoring voice models

### Resource Requirements

- **GPU**: Not required (CPU-only)
- **Memory**: 4Gi (request), 8Gi (limit)
- **CPU**: 2 cores (request), 4 cores (limit)
- **Storage**: Persistent volume for voice model storage

## Configuration

### Environment Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_VOICE` | `en_US-amy-medium` | Default voice model to use |
| `--max-piper-procs` | `8` | Maximum concurrent TTS processes |
| `--data-dir` | `/data` | Directory for voice data |
| `--download-dir` | `/data` | Directory for downloading voices |

### Available Voice Models

Piper supports various voice models with different qualities:

#### English (US) Voices
- **amy**: low, medium quality variants
- **lessac**: medium quality, clear pronunciation
- **ryan**: high quality male voice
- **kusal**: medium quality
- **ljspeech**: high quality, trained on LJSpeech dataset

#### English (GB) Voices
- **alan**: low quality British accent

Each voice has different characteristics:
- **Low**: Faster, smaller size (~15-30MB), lower quality
- **Medium**: Balanced speed and quality (~50-100MB)
- **High**: Best quality, larger size (~100-200MB), slower

## Usage

### Accessing the Service

Within the cluster:
```
piper.piper.svc.cluster.local:10200
```

### Wyoming Protocol Integration

The service implements the Wyoming protocol for TTS:

#### Home Assistant Configuration
```yaml
# In configuration.yaml
wyoming:
  - name: "Piper"
    host: piper.piper.svc.cluster.local
    port: 10200
```

### Testing the Service

Port-forward for local testing:
```bash
kubectl port-forward -n piper svc/piper 10200:10200
```

### Example TTS Request

Using Wyoming protocol client:
```python
from wyoming.tts import synthesize

# Connect to Piper
async with WyomingClient('piper.piper.svc.cluster.local', 10200) as client:
    # Generate speech
    audio = await client.synthesize(
        text="Hello, this is Piper speaking",
        voice="en_US-amy-low"
    )
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n piper

# View main container logs
kubectl logs -n piper deployment/piper -c piper

# View voice manager logs
kubectl logs -n piper deployment/piper -c voice-manager

# Check available voices
kubectl exec -n piper deployment/piper -- ls -la /data/*.onnx
```

### Managing Voice Models

#### List Available Voices
```bash
kubectl exec -n piper deployment/piper -- ls -la /data/
```

#### Voice Model Sizes
- **Low quality**: ~15-30 MB per voice
- **Medium quality**: ~50-100 MB per voice
- **High quality**: ~100-200 MB per voice

#### Manual Voice Download
If needed, you can manually download voices:
```bash
kubectl exec -n piper deployment/piper -- wget \
  https://github.com/rhasspy/piper/releases/download/2023.11.14-2/en_US-amy-medium.onnx \
  -O /data/en_US-amy-medium.onnx
```

### Changing Default Voice

1. Edit the ConfigMap:
```bash
kubectl edit configmap piper-configmap -n piper
```

2. Update deployment args if needed:
```bash
kubectl edit deployment piper -n piper
```

3. Restart the deployment:
```bash
kubectl rollout restart deployment/piper -n piper
```

## Troubleshooting

### Pod Not Starting

1. **Check node availability**:
```bash
kubectl get nodes -o wide
```

2. **Verify node affinity**:
```bash
kubectl describe pod -n piper -l app=piper
```

3. **Check storage**:
```bash
kubectl get pvc -n piper
```

### No Audio Output

1. **Verify voice model exists**:
```bash
kubectl exec -n piper deployment/piper -- ls -la /data/*.onnx
```

2. **Check logs for errors**:
```bash
kubectl logs -n piper deployment/piper -c piper | grep ERROR
```

3. **Test with different voice**:
   - Try using a different voice model
   - Ensure the voice file and its JSON config exist

### High CPU Usage

1. **Monitor CPU**:
```bash
kubectl top pod -n piper
```

2. **Reduce concurrent processes**:
   - Lower `--max-piper-procs` value
   - Use lower quality voices for better performance

### Voice Download Issues

1. **Check voice manager logs**:
```bash
kubectl logs -n piper deployment/piper -c voice-manager
```

2. **Verify internet connectivity**:
```bash
kubectl exec -n piper deployment/piper -- wget -O- https://github.com
```

3. **Check storage space**:
```bash
kubectl exec -n piper deployment/piper -- df -h /data
```

## Performance Tuning

### CPU Optimization

- **Process count**: Adjust `--max-piper-procs` based on CPU cores
- **Voice selection**: Use lower quality voices for faster synthesis
- **Caching**: Voice models are cached in memory after first use

### Quality vs Speed Trade-offs

| Voice Quality | Speed | CPU Usage | Use Case |
|--------------|-------|-----------|----------|
| Low | Fast | Low | Real-time responses, IoT |
| Medium | Moderate | Moderate | General use, assistants |
| High | Slow | High | Audiobooks, presentations |

### Scaling Considerations

For high-traffic scenarios:
```yaml
# Increase replicas
spec:
  replicas: 2
  
# Add HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: piper-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: piper
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Integration Examples

### Python Integration
```python
import asyncio
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize

async def text_to_speech(text, voice="en_US-amy-low"):
    client = AsyncTcpClient('piper.piper.svc.cluster.local', 10200)
    await client.connect()
    
    # Send synthesize request
    await client.send(Synthesize(
        text=text,
        voice=voice
    ))
    
    # Receive audio data
    audio_data = await client.receive_audio()
    await client.disconnect()
    
    return audio_data
```

### Node.js Integration
```javascript
const net = require('net');

function synthesizeSpeech(text, voice = 'en_US-amy-low') {
    return new Promise((resolve, reject) => {
        const client = net.createConnection({
            host: 'piper.piper.svc.cluster.local',
            port: 10200
        });
        
        client.on('connect', () => {
            // Send Wyoming protocol message
            const message = {
                type: 'synthesize',
                data: { text, voice }
            };
            client.write(JSON.stringify(message));
        });
        
        let audioBuffer = Buffer.alloc(0);
        client.on('data', (data) => {
            audioBuffer = Buffer.concat([audioBuffer, data]);
        });
        
        client.on('end', () => {
            resolve(audioBuffer);
        });
    });
}
```

### Home Assistant Automation
```yaml
automation:
  - alias: "Announce Weather"
    trigger:
      platform: time
      at: "08:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: media_player.living_room
          message: "Good morning! Today's weather is sunny with a high of 75 degrees."
          options:
            voice: "en_US-amy-medium"
```

## Security Considerations

- Service runs as non-root user (UID 1000)
- No external network access required after initial setup
- Voice models are read-only after download
- Consider network policies to restrict access

## Monitoring

Recommended metrics to monitor:
- CPU and memory usage
- TTS request rate and latency
- Voice model disk usage
- Error rates by voice model
- Concurrent process count

### Prometheus Metrics

Add Prometheus annotations:
```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

## Backup and Recovery

### Voice Model Backup

Voice models are stored in the PVC. To backup:
```bash
# Create snapshot of PVC
kubectl snapshot create piper-voices-backup -n piper
```

### Recovery

1. Restore PVC from backup
2. Restart deployment
3. Voice manager will verify models

## Future Improvements

- [ ] Add Prometheus metrics exporter
- [ ] Implement voice model version management
- [ ] Create web UI for voice selection
- [ ] Add support for SSML (Speech Synthesis Markup Language)
- [ ] Implement request queuing for better resource management
- [ ] Add voice cloning capabilities
- [ ] Create Grafana dashboard for monitoring
- [ ] Add multi-language support
