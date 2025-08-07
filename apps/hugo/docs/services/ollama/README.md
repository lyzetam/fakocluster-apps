# Ollama AI Model Server

## Overview

Ollama is a local AI model server deployed in the Fako cluster that provides a unified API for running large language models (LLMs). It runs on GPU acceleration and manages multiple AI models, making them available for various applications including Home Assistant integrations, coding assistants, and general AI tasks.

## Key Features

- **GPU Acceleration**: Optimized for RTX 5070 with 12GB VRAM
- **Model Management**: Automatic downloading and lifecycle management of models
- **Multiple Model Support**: Hosts various models from small (0.5B) to large (32B+)
- **RESTful API**: Compatible with OpenAI-style APIs
- **Persistent Storage**: Models cached to avoid re-downloading
- **Auto-scaling**: Memory management with model unloading

## Architecture

### Components

1. **Deployment**: Single-replica GPU deployment pinned to the `yeezyai` node
2. **Services**: 
   - ClusterIP service on port 11434
   - NodePort service for external access
3. **Storage**: PersistentVolumeClaim for model storage
4. **ConfigMaps**: 
   - General configuration
   - GPU-specific settings
5. **Sidecar Container**: Model manager for automatic model downloads

### Resource Requirements

- **GPU**: 1 NVIDIA GPU (RTX 5070)
- **Memory**: 12Gi (request), 36Gi (limit)
- **CPU**: 4 cores (request), 8 cores (limit)
- **Storage**: Persistent volume for model storage

## Configuration

### General Settings (ollama-configmap)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OLLAMA_HOST` | `0.0.0.0` | Bind address for the API server |
| `OLLAMA_ORIGINS` | `*` | CORS origins allowed |
| `OLLAMA_MODELS` | `/root/.ollama/models` | Model storage directory |
| `OLLAMA_DEBUG` | `false` | Enable debug logging |
| `OLLAMA_NOHISTORY` | `false` | Keep conversation history |

### GPU Settings (ollama-gpu-configmap)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OLLAMA_GPU_LAYERS` | `999` | Force all layers to GPU |
| `OLLAMA_GPU_MEMORY` | `12G` | GPU memory allocation |
| `OLLAMA_NUM_PARALLEL` | `2` | Concurrent request handling |
| `OLLAMA_NUM_THREAD` | `8` | CPU threads for operations |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Models kept in GPU memory |
| `OLLAMA_KEEP_ALIVE` | `5m` | Model keep-alive duration |

## Available Models

The model manager automatically downloads and maintains these models:

### Small Models (0.5B - 4B)
- **qwen2.5:0.5b** - Ultra-lightweight model
- **llama3.2:3b** - Efficient general-purpose model
- **phi3:mini** - Microsoft's compact model

### Medium Models (6B - 8B)
- **qwen3:8b** - Home Assistant specialized
- **llama3.1:8b** - Latest Llama model
- **deepseek-coder:6.7b-instruct** - Code-focused model

### Large Models (13B - 32B)
- **deepseek-r1:14b** - Enhanced for autonomous agents
- **ishumilin/deepseek-r1-coder-tools:14b** - Optimized for Cline
- **qwen:32b** - Large general-purpose model

## Usage

### Accessing the Service

Within the cluster:
```
http://ollama-gpu.ollama.svc.cluster.local:11434
```

### API Examples

#### List Available Models
```bash
curl http://ollama-gpu.ollama.svc.cluster.local:11434/api/tags
```

#### Generate Text
```bash
curl -X POST http://ollama-gpu.ollama.svc.cluster.local:11434/api/generate \
  -d '{
    "model": "llama3.1:8b",
    "prompt": "Explain kubernetes in simple terms"
  }'
```

#### Chat Completion (OpenAI Compatible)
```bash
curl -X POST http://ollama-gpu.ollama.svc.cluster.local:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### Integration with Applications

#### Cline/VS Code
```json
{
  "api_provider": "ollama",
  "ollama_base_url": "http://ollama-gpu.ollama.svc.cluster.local:11434",
  "ollama_model_id": "deepseek-r1:14b"
}
```

#### Home Assistant
```yaml
# In configuration.yaml
openai_conversation:
  - name: "Local Ollama"
    api_key: "dummy"  # Ollama doesn't need API key
    base_url: "http://ollama-gpu.ollama.svc.cluster.local:11434/v1"
    model: "qwen3:8b"
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n ollama

# View logs
kubectl logs -n ollama deployment/ollama-gpu

# Check model manager logs
kubectl logs -n ollama deployment/ollama-gpu -c model-manager

# Monitor GPU usage
kubectl exec -n ollama deployment/ollama-gpu -- nvidia-smi
```

### Managing Models

#### List Installed Models
```bash
kubectl exec -n ollama deployment/ollama-gpu -- ollama list
```

#### Pull a New Model
```bash
kubectl exec -n ollama deployment/ollama-gpu -- ollama pull model-name
```

#### Remove a Model
```bash
kubectl exec -n ollama deployment/ollama-gpu -- ollama rm model-name
```

### Model Storage Management

Models are stored at `/root/.ollama/models`. Storage usage varies by model:

- **Small models (0.5B-3B)**: 1-3 GB each
- **Medium models (6B-8B)**: 4-8 GB each
- **Large models (13B-32B)**: 8-20 GB each

## Troubleshooting

### Pod Not Starting

1. **Check GPU availability**:
```bash
kubectl describe node yeezyai | grep -A10 "Allocated resources"
```

2. **Verify GPU runtime**:
```bash
kubectl get runtimeclass nvidia
```

3. **Check events**:
```bash
kubectl describe pod -n ollama -l app=ollama-gpu
```

### Out of Memory Errors

1. **Reduce loaded models**:
   - Set `OLLAMA_MAX_LOADED_MODELS` to `1`
   - Decrease `OLLAMA_KEEP_ALIVE` duration

2. **Use quantized models**:
   - Choose models with `:q4_0` or `:q4_K_M` tags

3. **Monitor GPU memory**:
```bash
kubectl exec -n ollama deployment/ollama-gpu -- nvidia-smi
```

### Slow Response Times

1. **Check GPU utilization**:
```bash
watch -n 1 'kubectl exec -n ollama deployment/ollama-gpu -- nvidia-smi'
```

2. **Reduce parallel requests**:
   - Lower `OLLAMA_NUM_PARALLEL` value

3. **Use smaller models** for faster inference

### Model Download Issues

1. **Check model manager logs**:
```bash
kubectl logs -n ollama -l app=ollama-gpu -c model-manager
```

2. **Verify storage space**:
```bash
kubectl exec -n ollama deployment/ollama-gpu -- df -h /root/.ollama
```

## Performance Tuning

### GPU Optimization

- **Layer allocation**: `OLLAMA_GPU_LAYERS=999` ensures full GPU usage
- **Memory management**: Leave ~500MB for system overhead
- **Batch processing**: Adjust `OLLAMA_NUM_PARALLEL` based on workload

### Model Selection

Choose models based on use case:
- **Coding**: `deepseek-coder`, `deepseek-r1-coder-tools`
- **General chat**: `llama3.1:8b`, `qwen3:8b`
- **Resource-constrained**: `qwen2.5:0.5b`, `phi3:mini`

### Memory Optimization

```yaml
# For limited GPU memory
OLLAMA_GPU_MEMORY: "11G"  # Leave more for system
OLLAMA_MAX_LOADED_MODELS: "1"
OLLAMA_KEEP_ALIVE: "1m"
```

## Security Considerations

- Service runs with limited permissions
- CORS is open (`OLLAMA_ORIGINS: "*"`) - restrict in production
- No authentication by default - consider adding proxy authentication
- Models are stored with fsGroup 1000 permissions

## Monitoring

Key metrics to monitor:
- GPU utilization and memory usage
- Model loading/unloading frequency
- API response times
- Error rates per model
- Storage usage trends

### Prometheus Metrics

Ollama exposes metrics at `/metrics`:
```bash
curl http://ollama-gpu.ollama.svc.cluster.local:11434/metrics
```

## Backup and Recovery

### Model Backup

Models are stored in the PVC. To backup:
```bash
# Create backup job
kubectl create job ollama-backup -n ollama --from=cronjob/backup-ollama
```

### Recovery

1. Restore PVC from backup
2. Restart deployment to reload models

## Integration Examples

### Python Client
```python
import requests

def query_ollama(prompt, model="llama3.1:8b"):
    url = "http://ollama-gpu.ollama.svc.cluster.local:11434/api/generate"
    response = requests.post(url, json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    return response.json()['response']
```

### Node.js Integration
```javascript
const axios = require('axios');

async function generateText(prompt) {
    const response = await axios.post(
        'http://ollama-gpu.ollama.svc.cluster.local:11434/api/generate',
        {
            model: 'llama3.1:8b',
            prompt: prompt,
            stream: false
        }
    );
    return response.data.response;
}
```

## Future Improvements

- [ ] Add authentication layer
- [ ] Implement model version pinning
- [ ] Create Grafana dashboards
- [ ] Add automatic model pruning based on usage
- [ ] Implement request queuing for better resource management
- [ ] Add support for fine-tuned models
- [ ] Create model recommendation system based on task
