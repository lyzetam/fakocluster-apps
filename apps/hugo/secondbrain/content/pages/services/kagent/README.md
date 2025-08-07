# KAgent - Kubernetes AI Agent Framework

## Overview

KAgent is a Kubernetes-native AI agent framework deployed in the Fako cluster. It provides a platform for deploying and managing AI agents that can interact with various systems through the Model Context Protocol (MCP). Agents can be configured with different AI models, specialized knowledge, and tool access. The framework supports multiple AI providers including OpenAI, Ollama, and GPUStack, making it flexible for various use cases from Kubernetes operations to code generation.

## Key Features

- **Kubernetes Native**: Custom Resource Definitions (CRDs) for agents
- **Multi-Provider Support**: OpenAI, Ollama, GPUStack integration
- **MCP Tool Integration**: Connect agents to MCP servers for extended capabilities
- **Custom Agents**: Define agents with specific skills and knowledge
- **Helm Deployment**: Managed via Flux Helm controller
- **Model Flexibility**: Support for various AI models
- **System Message Customization**: Tailor agent behavior
- **External Secret Management**: Secure API key storage

## Architecture

### Components

1. **Helm Release**: Main kagent deployment
2. **CRDs**: Agent and ModelConfig custom resources
3. **Controller**: Manages agent lifecycle
4. **Service**: ClusterIP on port 80
5. **External Secrets**: API keys from AWS Secrets Manager
6. **Agent Definitions**: Custom agent configurations

### Resource Requirements

- **Memory**: 512Mi (request), 2Gi (limit)
- **CPU**: 250m (request), 1000m (limit)
- **Storage**: Minimal, agents are stateless

## Configuration

### Provider Configuration

Currently configured providers:
- **OpenAI**: Using external secret for API key
- Additional providers can be configured (Ollama, GPUStack)

### Agent Types

Example agents included:
1. **k8s-operator**: Kubernetes management agent
2. **deepseek-r1-coder**: Code generation agent
3. **qwen3-8b**: General purpose agent

## Usage

### Creating an Agent

Define an agent using the CRD:
```yaml
apiVersion: kagent.dev/v1alpha1
kind: Agent
metadata:
  name: my-agent
  namespace: kagent
spec:
  description: "My custom AI agent"
  modelConfig: "openai-gpt4"  # Reference to ModelConfig
  systemMessage: |
    You are a helpful assistant specialized in...
  tools:
    - name: kubernetes-mcp
      endpoint: "http://kubernetes-mcp-server:80"
```

### Model Configuration

Define available models:
```yaml
apiVersion: kagent.dev/v1alpha1
kind: ModelConfig
metadata:
  name: openai-gpt4
  namespace: kagent
spec:
  provider: openai
  model: gpt-4
  temperature: 0.7
  maxTokens: 4096
```

### Interacting with Agents

Access agents via the service:
```bash
# Port forward to access locally
kubectl port-forward -n kagent svc/kagent 8080:80

# Send request to agent
curl -X POST http://localhost:8080/agents/k8s-operator/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List all pods in default namespace"}'
```

## Agent Examples

### Kubernetes Operator Agent

Specialized for cluster management:
```yaml
spec:
  description: Advanced Kubernetes operator with MCP tools
  modelConfig: ollama-qwen3-30b-a3b
  systemMessage: |
    You are an expert Kubernetes operator...
    - List and inspect all Kubernetes resources
    - View pod logs and execute commands
    - Generate and validate manifests
    - Analyze cluster health
```

### Code Generation Agent

For development tasks:
```yaml
spec:
  description: Expert coder with deep thinking capabilities
  modelConfig: deepseek-r1
  systemMessage: |
    You are an expert programmer...
    - Write clean, efficient code
    - Follow best practices
    - Provide detailed explanations
```

## Operations

### Checking Service Status

```bash
# Check kagent pods
kubectl get pods -n kagent

# View controller logs
kubectl logs -n kagent -l app.kubernetes.io/name=kagent

# List agents
kubectl get agents -n kagent
```

### Managing Agents

```bash
# Create new agent
kubectl apply -f my-agent.yaml

# Update agent configuration
kubectl edit agent my-agent -n kagent

# Delete agent
kubectl delete agent my-agent -n kagent
```

### Monitoring Agent Activity

```bash
# View agent logs
kubectl logs -n kagent -l agent=my-agent

# Check agent metrics (if enabled)
kubectl port-forward -n kagent svc/kagent-metrics 9090:9090
```

## Troubleshooting

### Agent Not Responding

1. **Check agent status**:
```bash
kubectl describe agent my-agent -n kagent
```

2. **Verify model configuration**:
```bash
kubectl get modelconfig -n kagent
```

3. **Check API keys**:
```bash
kubectl get secret kagent-openai -n kagent
```

### API Key Issues

1. **Verify external secret**:
```bash
kubectl describe externalsecret kagent-openai -n kagent
```

2. **Check secret data**:
```bash
kubectl get secret kagent-openai -n kagent -o yaml
```

### Model Connection Failures

1. **For Ollama models**:
```bash
# Check Ollama service
kubectl get svc -n ollama

# Test connection
kubectl exec -n kagent deployment/kagent -- \
  curl -s http://ollama.ollama.svc.cluster.local:11434/api/tags
```

2. **For OpenAI**:
```bash
# Test API key
kubectl exec -n kagent deployment/kagent -- \
  curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Security Considerations

### API Key Management
- All API keys stored in AWS Secrets Manager
- Accessed via External Secrets Operator
- Never hardcoded in configurations

### Agent Permissions
- Agents run with limited permissions
- MCP tools require explicit configuration
- Network policies can restrict access

### Best Practices
1. **Limit agent capabilities**: Only grant necessary tools
2. **Monitor usage**: Track API calls and costs
3. **Rotate keys**: Regular API key rotation
4. **Audit agents**: Review agent activities
5. **Namespace isolation**: Separate sensitive agents

## MCP Tool Integration

### Available MCP Servers

Agents can connect to:
- `kubernetes-mcp-server`: Kubernetes operations
- `filesystem-mcp`: File system access
- `postgres-mcp`: Database queries
- `github-mcp`: Repository management

### Configuring Tools

```yaml
spec:
  tools:
    - name: kubernetes-mcp
      endpoint: "http://kubernetes-mcp-server.mcp-servers:80"
      capabilities:
        - read
        - write
    - name: postgres-mcp
      endpoint: "http://postgres-mcp-server.mcp-servers:80"
      capabilities:
        - query
```

## Advanced Configuration

### Custom Provider Setup

Add new AI provider:
```yaml
# In values.yaml
providers:
  anthropic:
    existingSecret: kagent-anthropic
    existingSecretKey: ANTHROPIC_API_KEY
```

### Agent Templates

Create reusable templates:
```yaml
apiVersion: kagent.dev/v1alpha1
kind: AgentTemplate
metadata:
  name: base-k8s-agent
spec:
  systemMessage: |
    Base Kubernetes agent configuration...
  tools:
    - kubernetes-mcp
```

### Rate Limiting

Configure rate limits:
```yaml
spec:
  rateLimits:
    requestsPerMinute: 60
    tokensPerMinute: 100000
```

## Monitoring

### Key Metrics
- Agent request count
- Response times
- Token usage
- Error rates
- Active agents

### Prometheus Integration

```yaml
# ServiceMonitor for metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kagent
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: kagent
```

### Cost Tracking

Monitor API usage:
```bash
# OpenAI usage
kubectl exec -n kagent deployment/kagent -- \
  ./scripts/check-usage.sh
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor agent errors
   - Check API usage
   - Review costs

2. **Weekly**:
   - Update agent configurations
   - Review agent performance
   - Clean unused agents

3. **Monthly**:
   - Update kagent version
   - Rotate API keys
   - Audit agent access

### Backup and Recovery

```bash
# Backup agent definitions
kubectl get agents -n kagent -o yaml > agents-backup.yaml

# Backup model configs
kubectl get modelconfigs -n kagent -o yaml > models-backup.yaml
```

### Version Updates

```bash
# Update Helm release
kubectl edit helmrelease kagent -n kagent

# Update CRDs if needed
kubectl apply -f apps/base/kagent/release-crds.yaml
```

## Use Cases

### DevOps Automation
- Kubernetes troubleshooting
- Deployment automation
- Log analysis
- Performance optimization

### Development Support
- Code generation
- Code review
- Documentation writing
- Bug analysis

### Operations
- Incident response
- System monitoring
- Report generation
- Workflow automation

## Future Improvements

- [ ] Add web UI for agent management
- [ ] Implement agent chaining
- [ ] Add conversation history storage
- [ ] Create agent marketplace
- [ ] Implement fine-tuning support
- [ ] Add multi-tenant isolation
- [ ] Create agent testing framework
- [ ] Add cost optimization features
- [ ] Implement agent versioning
- [ ] Add observability dashboards
