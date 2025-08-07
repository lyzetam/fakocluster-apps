# GPUStack Proxy - Secure Tunnel Access Service

## Overview

GPUStack Proxy is a Cloudflare Tunnel-based proxy service deployed in the Fako cluster that provides secure external access to the GPUStack AI inference platform. It uses Cloudflare's cloudflared to create an encrypted tunnel between the cluster and Cloudflare's edge network, eliminating the need for exposed public IPs or open inbound ports. The service includes automatic endpoint synchronization with AWS Secrets Manager for seamless integration with AI applications.

## Key Features

- **Cloudflare Tunnel**: Zero-trust secure access without exposed ports
- **High Availability**: Multi-replica cloudflared deployment
- **Automatic Failover**: Built-in redundancy and health checks
- **Endpoint Sync**: Automated endpoint updates to AWS Secrets Manager
- **SSL/TLS Termination**: Handled by Cloudflare edge
- **DDoS Protection**: Cloudflare's built-in protection
- **No Public IP Required**: Works behind NAT/firewall
- **Metrics & Monitoring**: Built-in metrics endpoint

## Architecture

### Components

1. **Cloudflared Deployment**: 2 replicas for HA
2. **Service**: ClusterIP routing to GPUStack
3. **ConfigMap**: Tunnel configuration
4. **External Secrets**: Tunnel credentials from AWS
5. **Endpoint Sync Job**: Updates AWS with tunnel info
6. **Ingress**: Optional Kubernetes ingress

### Resource Requirements

- **Memory**: 128Mi (request), 256Mi (limit)
- **CPU**: 250m (request), 500m (limit)
- **Replicas**: 2 for high availability

## Configuration

### Tunnel Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Tunnel Name | `audiobooks` | Cloudflare tunnel identifier |
| Hostname | `gpustack.landryzetam.net` | External access URL |
| Target | `http://gpustack:80` | Internal GPUStack service |
| Metrics Port | `2000` | Health and metrics endpoint |

### Service Routing

```yaml
ingress:
  - hostname: gpustack.landryzetam.net
    service: http://gpustack:80
  - hostname: hello.example.com
    service: hello_world  # Debug endpoint
  - service: http_status:404  # Catch-all
```

## Usage

### Accessing GPUStack

External access via Cloudflare:
```
https://gpustack.landryzetam.net
```

Internal cluster access:
```
http://gpustack.gpustack-proxy.svc.cluster.local
```

### API Access

For AI applications:
```python
import openai

# Configure OpenAI client for GPUStack
client = openai.OpenAI(
    base_url="https://gpustack.landryzetam.net/v1",
    api_key="your-api-key"
)
```

### Health Monitoring

Check tunnel status:
```bash
# Check cloudflared health
kubectl get pods -n gpustack-proxy

# View tunnel metrics
kubectl port-forward -n gpustack-proxy deployment/cloudflared 2000:2000
curl http://localhost:2000/metrics
```

## Operations

### Tunnel Management

#### Check Tunnel Status
```bash
# View cloudflared logs
kubectl logs -n gpustack-proxy -l app=cloudflared

# Check connection status
kubectl exec -n gpustack-proxy deployment/cloudflared -- \
  cloudflared tunnel info audiobooks
```

#### Restart Tunnel
```bash
# Rolling restart
kubectl rollout restart deployment/cloudflared -n gpustack-proxy

# Monitor restart
kubectl rollout status deployment/cloudflared -n gpustack-proxy
```

### Endpoint Synchronization

The endpoint sync job updates AWS Secrets Manager:
```bash
# Check sync job
kubectl get jobs -n gpustack-proxy

# View sync logs
kubectl logs -n gpustack-proxy job/endpoint-sync
```

### Credential Rotation

Update tunnel credentials:
```bash
# Update secret in AWS
aws secretsmanager update-secret \
  --secret-id cloudflare/tunnel-credentials \
  --secret-string file://new-credentials.json

# Restart cloudflared
kubectl rollout restart deployment/cloudflared -n gpustack-proxy
```

## Troubleshooting

### Tunnel Not Connecting

1. **Check credentials**:
```bash
kubectl get secret tunnel-credentials -n gpustack-proxy
kubectl describe externalsecret -n gpustack-proxy
```

2. **Verify tunnel exists**:
```bash
# List tunnels (requires Cloudflare API token)
cloudflared tunnel list
```

3. **Check DNS**:
```bash
# Verify DNS points to tunnel
dig gpustack.landryzetam.net
```

### Connection Issues

1. **Test internal service**:
```bash
# Port forward to GPUStack directly
kubectl port-forward -n gpustack-proxy svc/gpustack 8080:80
curl http://localhost:8080/health
```

2. **Check cloudflared health**:
```bash
kubectl exec -n gpustack-proxy deployment/cloudflared -- \
  curl -s http://localhost:2000/ready
```

### High Latency

1. **Check metrics**:
```bash
curl http://localhost:2000/metrics | grep cloudflared_tunnel_
```

2. **Verify closest Cloudflare PoP**:
```bash
curl -s https://gpustack.landryzetam.net/cdn-cgi/trace | grep colo
```

## Security Considerations

### Zero Trust Architecture
- No inbound ports required
- All traffic encrypted via Cloudflare
- Authentication at edge possible

### Access Control
- Cloudflare Access policies
- API key authentication
- IP allowlisting available

### Best Practices
1. **Rotate credentials**: Regular tunnel credential rotation
2. **Monitor access**: Review Cloudflare analytics
3. **Enable WAF**: Use Cloudflare WAF rules
4. **Rate limiting**: Configure at Cloudflare edge
5. **Audit logs**: Enable Cloudflare audit logs

## Performance Optimization

### Cloudflare Settings

Optimize for API traffic:
```json
{
  "cache_level": "bypass",
  "websockets": true,
  "http2": true,
  "http3": true,
  "0rtt": true
}
```

### Connection Pooling

cloudflared configuration:
```yaml
originRequest:
  connectTimeout: 30s
  noTLSVerify: false
  keepAliveConnections: 100
  keepAliveTimeout: 90s
```

### Load Balancing

With multiple replicas:
- Automatic failover
- Connection distribution
- Health-based routing

## Monitoring

### Key Metrics

- `cloudflared_tunnel_ha_connections`: Active connections
- `cloudflared_tunnel_request_errors`: Error rate
- `cloudflared_tunnel_response_time`: Latency
- `cloudflared_tunnel_concurrent_requests`: Current load
- `cloudflared_tunnel_authentication_success`: Auth metrics

### Cloudflare Analytics

Available metrics:
- Request volume
- Response times
- Error rates
- Bandwidth usage
- Security events

### Alerts

Configure alerts:
```yaml
# Tunnel down alert
- alert: CloudflaredTunnelDown
  expr: up{job="cloudflared"} == 0
  for: 5m
  annotations:
    summary: "Cloudflare tunnel is down"
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor tunnel health
   - Check error logs
   - Review traffic patterns

2. **Weekly**:
   - Analyze performance metrics
   - Review security events
   - Check certificate status

3. **Monthly**:
   - Update cloudflared version
   - Rotate credentials
   - Review access policies

### Version Updates

```bash
# Update cloudflared image
kubectl set image deployment/cloudflared \
  cloudflared=cloudflare/cloudflared:2025.8.0 \
  -n gpustack-proxy
```

### Backup Configuration

```bash
# Export tunnel config
kubectl get configmap cloudflared -n gpustack-proxy -o yaml > tunnel-config-backup.yaml

# Backup credentials (encrypted)
kubectl get secret tunnel-credentials -n gpustack-proxy -o yaml > tunnel-creds-backup.yaml
```

## Advanced Configuration

### Multiple Backends

Route to different services:
```yaml
ingress:
  - hostname: api.domain.com
    service: http://api-service:80
  - hostname: app.domain.com
    service: http://app-service:3000
  - hostname: gpustack.domain.com
    service: http://gpustack:80
```

### Custom Headers

Add headers for backend:
```yaml
originRequest:
  httpHostHeader: "gpustack.internal"
  originServerName: "gpustack.internal"
  caPool: "/etc/cloudflared/certs/ca.crt"
```

### Access Policies

Integrate with Cloudflare Access:
```yaml
# Require authentication
- hostname: gpustack.landryzetam.net
  service: http://gpustack:80
  originRequest:
    access:
      required: true
      teamDomain: "your-team"
```

## Integration Examples

### With Open WebUI

Configure Open WebUI to use proxy:
```yaml
env:
  OPENAI_API_BASE_URL: "https://gpustack.landryzetam.net/v1"
```

### With n8n Workflows

AI nodes configuration:
```json
{
  "baseURL": "https://gpustack.landryzetam.net/v1",
  "apiKey": "{{$credentials.gpustack.apiKey}}"
}
```

### With Python Applications

```python
import requests

response = requests.post(
    "https://gpustack.landryzetam.net/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"model": "llama2", "messages": messages}
)
```

## Cost Considerations

### Cloudflare Costs
- Free tier: 50 concurrent connections
- Pro tier: Higher limits
- Enterprise: Custom limits

### Bandwidth
- No bandwidth charges from Cloudflare
- Standard Kubernetes egress applies

### Optimization
- Enable compression
- Use HTTP/2 multiplexing
- Implement caching where appropriate

## Future Improvements

- [ ] Implement multi-region tunnels
- [ ] Add automatic failover between regions
- [ ] Create terraform module for tunnel setup
- [ ] Implement request queuing
- [ ] Add WebSocket support for streaming
- [ ] Create custom metrics exporter
- [ ] Implement automatic scaling based on load
- [ ] Add request/response logging
- [ ] Create backup tunnel configuration
- [ ] Implement tunnel health dashboard
