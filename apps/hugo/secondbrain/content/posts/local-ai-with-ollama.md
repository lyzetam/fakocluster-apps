---
title: "Running Local AI: My Experience with Ollama and GPU Acceleration"
date: 2025-01-07
draft: false
description: "Practical insights from running local LLMs with Ollama on Kubernetes using GPU acceleration"
tags: ["AI", "Ollama", "GPU", "LLM", "Self-Hosting", "Machine Learning"]
categories: ["AI/ML", "Projects"]
author: "Landry"
---

One of the most exciting aspects of the Fako Cluster is the ability to run large language models locally. With privacy concerns around cloud AI services and the desire for unlimited API usage, I decided to dive deep into self-hosting LLMs using Ollama. Here's what I've learned.

## The Hardware Foundation

Running LLMs locally requires serious GPU power. My setup:

- **GPU**: NVIDIA RTX 5070 with 12GB VRAM
- **Node**: Dedicated `yeezyai` node in the cluster
- **Memory**: 36GB RAM allocated to the Ollama pod

This configuration allows me to run models up to 32B parameters, though performance varies significantly based on model size.

## Why Ollama?

After evaluating several options (LocalAI, llama.cpp, text-generation-webui), I chose Ollama because:

1. **Simple API**: OpenAI-compatible endpoints
2. **Model Management**: Automatic downloading and caching
3. **Resource Efficiency**: Smart memory management
4. **Kubernetes-Ready**: Easy to containerize and scale

## Real-World Performance

Here's what I've observed running different model sizes:

### Small Models (0.5B - 3B parameters)
- **Examples**: qwen2.5:0.5b, llama3.2:3b
- **Performance**: Nearly instant responses
- **Use Cases**: Quick tasks, code completion, chat
- **Memory**: 1-3GB VRAM

### Medium Models (6B - 8B parameters)
- **Examples**: llama3.1:8b, deepseek-coder:6.7b
- **Performance**: 20-40 tokens/second
- **Use Cases**: General purpose, coding assistance
- **Memory**: 4-8GB VRAM

### Large Models (13B - 32B parameters)
- **Examples**: deepseek-r1:14b, qwen:32b
- **Performance**: 5-15 tokens/second
- **Use Cases**: Complex reasoning, detailed analysis
- **Memory**: 8-20GB VRAM (with quantization)

## Practical Implementation

### The Deployment Strategy

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-gpu
  namespace: ollama
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-gpu
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: yeezyai
      containers:
      - name: ollama
        image: ollama/ollama:latest
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 36Gi
        env:
        - name: OLLAMA_GPU_LAYERS
          value: "999"  # Force all layers to GPU
        - name: OLLAMA_MAX_LOADED_MODELS
          value: "1"    # Memory optimization
```

### Model Management Automation

I created a sidecar container to automatically download and maintain models:

```bash
#!/bin/bash
# Model manager script
MODELS=(
  "llama3.1:8b"
  "deepseek-coder:6.7b-instruct"
  "qwen3:8b"
)

for model in "${MODELS[@]}"; do
  if ! ollama list | grep -q "$model"; then
    echo "Pulling $model..."
    ollama pull "$model"
  fi
done
```

## Integration Success Stories

### 1. VS Code + Cline

My favorite integration is with Cline (formerly Continue) in VS Code:

```json
{
  "models": [{
    "title": "DeepSeek Coder",
    "provider": "ollama",
    "model": "deepseek-coder:6.7b-instruct",
    "apiBase": "http://localhost:11434"
  }]
}
```

Result: Code completion and assistance without sending code to external services.

### 2. Home Assistant Voice Assistant

Integrated with Home Assistant for voice commands:

```yaml
conversation:
  intents:
    HassLightControl:
      - sentences:
          - "turn on the {area} lights"
          - "lights on in {area}"

openai_conversation:
  - name: "Local Ollama"
    api_key: "dummy"
    base_url: "http://ollama-gpu.ollama.svc.cluster.local:11434/v1"
    model: "qwen3:8b"
```

### 3. n8n Workflow Automation

Using Ollama in n8n workflows for text processing:

```javascript
// n8n Function node
const response = await $http.post(
  'http://ollama-gpu:11434/api/generate',
  {
    model: 'llama3.1:8b',
    prompt: items[0].json.text,
    stream: false
  }
);
return [{json: {result: response.data.response}}];
```

## Challenges and Solutions

### GPU Memory Management

**Problem**: Models consuming all VRAM and crashing

**Solution**: 
```yaml
OLLAMA_GPU_MEMORY: "11G"  # Leave 1GB for system
OLLAMA_KEEP_ALIVE: "5m"   # Unload models after 5 minutes
```

### Model Selection Paralysis

**Problem**: Too many models to choose from

**Solution**: Created a decision matrix:
- **Coding**: deepseek-coder or deepseek-r1
- **General Chat**: llama3.1:8b
- **Quick Tasks**: qwen2.5:0.5b
- **Home Assistant**: qwen3:8b (optimized for commands)

### Network Latency

**Problem**: Slow responses over network

**Solution**: 
- NodePort service for local access
- Connection pooling in applications
- Response streaming for better UX

## Cost Analysis

Running Ollama locally vs cloud APIs:

| Service | Monthly Cost | Requests/Month |
|---------|-------------|----------------|
| OpenAI GPT-4 | $300+ | 100K |
| Claude Pro | $20 | Limited |
| **Local Ollama** | $0* | Unlimited |

*Excluding electricity costs (~$10/month for 24/7 GPU usage)

## Performance Optimization Tips

1. **Quantization is Your Friend**
   ```bash
   # Use quantized models for better performance
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```

2. **Layer Allocation**
   ```yaml
   OLLAMA_GPU_LAYERS: "999"  # All layers on GPU
   OLLAMA_NUM_THREAD: "8"    # Match CPU cores
   ```

3. **Batch Processing**
   ```python
   # Process multiple prompts efficiently
   async def batch_inference(prompts):
       tasks = [ollama_generate(p) for p in prompts]
       return await asyncio.gather(*tasks)
   ```

## Future Plans

My roadmap for local AI:

1. **Fine-tuning Pipeline**: Custom models for specific tasks
2. **Multi-GPU Support**: Scale to larger models
3. **RAG Implementation**: Local knowledge base integration
4. **Voice Pipeline**: Real-time voice processing
5. **Model Mixing**: Ensemble approaches for better results

## Lessons Learned

1. **Start Small**: Begin with 7B models and scale up
2. **Monitor Everything**: GPU metrics are crucial
3. **Cache Aggressively**: Model loading is expensive
4. **Choose Wisely**: Not every task needs a 32B model
5. **Embrace Quantization**: Quality loss is minimal

## Is It Worth It?

Absolutely! The benefits:

- **Privacy**: Your data never leaves your infrastructure
- **Cost**: One-time hardware investment vs recurring API costs
- **Control**: Choose models, update on your schedule
- **Learning**: Deep understanding of LLM operations
- **Integration**: Seamless with local services

## Getting Started

If you're interested in running local AI:

1. Start with a decent GPU (8GB+ VRAM)
2. Use Ollama for simplicity
3. Begin with smaller models
4. Monitor performance closely
5. Scale based on actual needs

The journey from cloud-dependent AI to fully local inference has been enlightening. Whether you're concerned about privacy, costs, or just love tinkering, local LLMs are more accessible than ever!

---

*Want to explore my Ollama setup? Check out the [Ollama project documentation](/pages/projects/ollama) or feel free to reach out with questions!*
