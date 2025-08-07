# MCP Servers - Model Context Protocol Services

## Overview

MCP (Model Context Protocol) Servers is a collection of specialized services deployed in the Fako cluster that extend AI capabilities by providing structured access to various tools and resources. These servers implement the Model Context Protocol, enabling AI assistants like Claude to interact with external systems, databases, APIs, and tools in a standardized way. Each MCP server provides specific functionality that can be consumed by AI agents for enhanced automation and integration.

## Key Features

- **Standardized Protocol**: All servers implement the Model Context Protocol
- **Tool Extension**: Provides AI assistants with new capabilities
- **Resource Access**: Structured access to external data sources
- **High Availability**: Multi-replica deployments for critical servers
- **Secure Integration**: RBAC and service accounts for each server
- **Shared Workspace**: Common storage for cross-server collaboration

## Architecture

### Components

1. **Multiple MCP Servers**: Each providing specialized functionality
   - kubernetes-mcp: Kubernetes cluster management
   - postgres-mcp: PostgreSQL database operations
   - filesystem-mcp: File system access
   - github-mcp: GitHub repository interactions
   - memory-mcp: Persistent memory/context storage
   - n8n-mcp: N8N workflow integration
   - puppeteer-mcp: Web automation
   - time-mcp: Time and scheduling utilities
   - weather-mcp: Weather data access
   - And more...

2. **Shared Resources**:
   - Namespace: `mcp-servers`
   - Shared workspace PVC for data exchange
   - Common service discovery

### Resource Requirements

Varies by server, typically:
- **Memory**: 128Mi-512Mi per server
- **CPU**: 100m-500m per server
- **Storage**: Shared workspace volume

## Available MCP Servers

### 1. Kubernetes MCP Server
**Purpose**: Kubernetes cluster management and operations

**Capabilities**:
- List/describe resources
- Apply/delete manifests
- Execute commands in pods
- Monitor cluster health
- Scale deployments

**Deployment**: 3 replicas for HA

### 2. PostgreSQL MCP Server
**Purpose**: Database operations and queries

**Capabilities**:
- Execute SQL queries
- Manage database schemas
- Import/export data
- Database administration

### 3. Filesystem MCP Server
**Purpose**: File system operations

**Capabilities**:
- Read/write files
- Directory operations
- File search and filtering
- Archive management

### 4. GitHub MCP Server
**Purpose**: GitHub repository interactions

**Capabilities**:
- Repository management
- Issue/PR operations
- Code search
- Workflow triggers

### 5. Memory MCP Server
**Purpose**: Persistent context storage

**Capabilities**:
- Store/retrieve context
- Session management
- Cross-conversation memory

### 6. N8N MCP Server
**Purpose**: Workflow automation integration

**Capabilities**:
- Trigger workflows
- Monitor executions
- Manage workflow data

### 7. Puppeteer MCP Server
**Purpose**: Web browser automation

**Capabilities**:
- Web scraping
- Form automation
- Screenshot capture
- Browser testing

### 8. Time MCP Server
**Purpose**: Time and date utilities

**Capabilities**:
- Timezone conversions
- Date calculations
- Scheduling helpers

### 9. Weather MCP Server
**Purpose**: Weather data access

**Capabilities**:
- Current weather
- Forecasts
- Historical data

## Usage

### For AI Assistants (Claude, etc.)

MCP servers are automatically discovered and available to AI assistants configured with MCP support. The assistant can:

1. **List available tools**:
   ```
   What MCP tools are available?
   ```

2. **Use specific tools**:
   ```
   Use the kubernetes MCP to list all pods in the default namespace
   ```

3. **Chain operations**:
   ```
   Check the weather, then create an N8N workflow to send alerts if it's raining
   ```

### Direct API Access

Each MCP server exposes a standard MCP API:

```bash
# Example: Query kubernetes-mcp
curl -X POST http://kubernetes-mcp-server.mcp-servers.svc.cluster.local/api/v1/tools \
  -H "Content-Type: application/json" \
  -d '{"method": "list_pods", "params": {"namespace": "default"}}'
```

## Operations

### Checking Server Status

```bash
# List all MCP servers
kubectl get deployments -n mcp-servers

# Check specific server
kubectl get pods -n mcp-servers -l app.kubernetes.io/name=kubernetes-mcp-server

# View logs
kubectl logs -n mcp-servers deployment/kubernetes-mcp-server
```

### Monitoring Health

```bash
# Check readiness
kubectl get endpoints -n mcp-servers

# Resource usage
kubectl top pods -n mcp-servers
```

### Scaling Servers

```bash
# Scale a specific server
kubectl scale deployment kubernetes-mcp-server -n mcp-servers --replicas=5

# Or edit deployment
kubectl edit deployment kubernetes-mcp-server -n mcp-servers
```

## Configuration

### Server-Specific Configuration

Each MCP server may have specific configuration needs:

#### Kubernetes MCP
- ServiceAccount with appropriate RBAC
- Cluster role bindings for operations
- Optional: Read-only mode flag

#### PostgreSQL MCP
- Database connection strings
- Credentials via secrets
- Connection pool settings

#### GitHub MCP
- GitHub API tokens
- Repository permissions
- Rate limiting configuration

### Shared Workspace

All servers can access shared workspace:
```yaml
volumeMounts:
- name: shared-workspace
  mountPath: /workspace
```

## Security Considerations

### RBAC and Permissions
- Each server runs with minimal required permissions
- Service accounts follow principle of least privilege
- Network policies restrict inter-service communication

### Authentication
- MCP protocol authentication
- Server-specific auth (GitHub tokens, DB passwords)
- Internal service mesh security

### Best Practices
1. **Audit Usage**: Monitor MCP tool usage
2. **Limit Permissions**: Grant only necessary permissions
3. **Rotate Credentials**: Regular credential rotation
4. **Network Isolation**: Use network policies
5. **Log Analysis**: Monitor for suspicious activity

## Troubleshooting

### Server Not Responding

1. **Check pod status**:
```bash
kubectl describe pod -n mcp-servers <pod-name>
```

2. **Verify service endpoints**:
```bash
kubectl get endpoints -n mcp-servers
```

3. **Check logs for errors**:
```bash
kubectl logs -n mcp-servers deployment/<server-name> --tail=50
```

### Permission Errors

1. **Verify RBAC**:
```bash
kubectl auth can-i --list --as=system:serviceaccount:mcp-servers:<sa-name>
```

2. **Check service account**:
```bash
kubectl get sa -n mcp-servers
kubectl describe sa <sa-name> -n mcp-servers
```

### Connection Issues

1. **Test connectivity**:
```bash
kubectl run test-pod --rm -it --image=busybox --restart=Never -- \
  wget -O- http://<server-name>.mcp-servers.svc.cluster.local/health
```

2. **Check DNS resolution**:
```bash
kubectl run test-pod --rm -it --image=busybox --restart=Never -- \
  nslookup <server-name>.mcp-servers.svc.cluster.local
```

## Integration Examples

### With AI Agents

```python
# Example: Using MCP in a custom AI agent
from mcp_client import MCPClient

# Initialize clients
k8s_client = MCPClient("kubernetes-mcp-server.mcp-servers.svc.cluster.local")
pg_client = MCPClient("postgres-mcp-server.mcp-servers.svc.cluster.local")

# Use tools
pods = await k8s_client.call_tool("list_pods", {"namespace": "default"})
db_result = await pg_client.call_tool("query", {"sql": "SELECT * FROM users"})
```

### With N8N Workflows

Create N8N workflows that leverage MCP servers:
1. Webhook trigger
2. Call MCP server via HTTP
3. Process results
4. Take actions

### With Monitoring

```yaml
# Prometheus ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-servers
  namespace: mcp-servers
spec:
  selector:
    matchLabels:
      app.kubernetes.io/part-of: mcp-servers
  endpoints:
  - port: metrics
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor server health
   - Check error rates
   - Review resource usage

2. **Weekly**:
   - Analyze usage patterns
   - Update server images
   - Review security logs

3. **Monthly**:
   - Audit permissions
   - Update configurations
   - Performance optimization

### Adding New MCP Servers

1. **Create deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-mcp-server
  namespace: mcp-servers
spec:
  # ... deployment spec
```

2. **Add service account** if needed
3. **Configure RBAC** for required permissions
4. **Create service** for discovery
5. **Update kustomization.yaml**

## Performance Optimization

### Resource Tuning
- Adjust replica counts based on usage
- Configure HPA for auto-scaling
- Optimize memory/CPU limits

### Caching Strategies
- Implement response caching
- Use shared workspace for data
- Cache external API responses

### Connection Pooling
- Database connection pools
- HTTP client connection reuse
- gRPC connection management

## Future Improvements

- [ ] Add more specialized MCP servers
- [ ] Implement server discovery service
- [ ] Create unified monitoring dashboard
- [ ] Add request routing/load balancing
- [ ] Implement rate limiting per client
- [ ] Add WebSocket support for streaming
- [ ] Create MCP server SDK/template
- [ ] Add server health check endpoints
- [ ] Implement distributed tracing
- [ ] Add cost tracking per operation
