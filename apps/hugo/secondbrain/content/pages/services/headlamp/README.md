# Headlamp Kubernetes Dashboard

## Overview

Headlamp is a user-friendly Kubernetes dashboard deployed in the Fako cluster. It provides a web-based UI for managing and monitoring Kubernetes resources across all namespaces. Headlamp offers an intuitive interface for both beginners and advanced users, with support for plugins and real-time updates. This deployment includes the Kubescape security plugin for enhanced cluster security visibility.

## Key Features

- **User-Friendly Interface**: Clean, modern UI for Kubernetes management
- **Real-Time Updates**: Live view of cluster resources and events
- **Multi-Resource Support**: Manage all Kubernetes resource types
- **Plugin Architecture**: Extensible with custom plugins
- **In-Cluster Mode**: Runs with cluster service account
- **Kubescape Integration**: Security scanning and compliance checks
- **Mobile Responsive**: Works on desktop and mobile devices

## Architecture

### Components

1. **Deployment**: Single-replica deployment
2. **Service**: ClusterIP service on port 80
3. **Ingress**: HTTPS access (configured separately)
4. **ServiceAccount**: Cluster-wide permissions for resource access
5. **Init Container**: Installs Kubescape plugin
6. **Plugin Volume**: EmptyDir for plugin storage

### Resource Requirements

- **Memory**: 128Mi (request), 512Mi (limit)
- **CPU**: 100m (request), 500m (limit)
- **Storage**: EmptyDir for plugins (ephemeral)

## Configuration

### Deployment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `-in-cluster` | Enabled | Run using in-cluster config |
| `-plugins-dir` | `/build/plugins` | Plugin directory location |
| Port | `4466` | Application HTTP port |
| Image | `ghcr.io/headlamp-k8s/headlamp:v0.33.0` | Headlamp version |

### RBAC Configuration

Headlamp runs with a ClusterRole that provides full access to:
- Core resources (pods, services, configmaps, etc.)
- Apps resources (deployments, statefulsets, etc.)
- Networking resources
- RBAC resources
- Storage resources
- Metrics
- CRDs (including Kubescape)

## Usage

### Accessing Headlamp

External access (requires ingress configuration):
```
https://headlamp.your-domain.com
```

Internal access:
```
http://headlamp.headlamp.svc.cluster.local
```

Port forwarding for local access:
```bash
kubectl port-forward -n headlamp svc/headlamp 8080:80
# Access at http://localhost:8080
```

### Navigation and Features

#### Dashboard Overview
- **Cluster Overview**: Node status, resource usage, events
- **Workloads**: Deployments, pods, jobs, cronjobs
- **Networking**: Services, ingresses, network policies
- **Storage**: PVCs, storage classes
- **Configuration**: ConfigMaps, secrets
- **Security**: RBAC, service accounts, Kubescape reports

#### Common Tasks

1. **View Pod Logs**:
   - Navigate to Workloads → Pods
   - Click on pod name
   - Select "Logs" tab

2. **Scale Deployment**:
   - Navigate to Workloads → Deployments
   - Click deployment name
   - Edit replica count

3. **Create Resources**:
   - Click "+" button
   - Paste YAML or use form
   - Apply to cluster

4. **Security Scanning** (Kubescape):
   - Navigate to Security section
   - View compliance reports
   - Check vulnerability scans

### Using the Kubescape Plugin

The Kubescape plugin provides:
- **Security Posture**: Overall cluster security score
- **Compliance**: NSA, MITRE compliance checks
- **Vulnerabilities**: Image vulnerability scanning
- **RBAC Analysis**: Permission analysis
- **Network Policies**: Policy recommendations

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n headlamp

# View logs
kubectl logs -n headlamp -l app.kubernetes.io/name=headlamp

# Check plugin installation
kubectl logs -n headlamp -l app.kubernetes.io/name=headlamp -c kubescape-plugin
```

### Plugin Management

#### List Installed Plugins
```bash
kubectl exec -n headlamp deployment/headlamp -- ls -la /build/plugins/
```

#### Add Custom Plugin
```bash
# Create ConfigMap with plugin
kubectl create configmap my-plugin --from-file=plugin.js -n headlamp

# Mount in deployment (edit deployment.yaml)
```

### Troubleshooting Access Issues

1. **Check service account**:
```bash
kubectl get sa headlamp -n headlamp
kubectl get clusterrolebinding headlamp
```

2. **Verify RBAC permissions**:
```bash
kubectl auth can-i --list --as=system:serviceaccount:headlamp:headlamp
```

## Troubleshooting

### Dashboard Not Loading

1. **Check pod status**:
```bash
kubectl describe pod -n headlamp -l app.kubernetes.io/name=headlamp
```

2. **Verify service endpoints**:
```bash
kubectl get endpoints -n headlamp
```

3. **Check ingress (if configured)**:
```bash
kubectl get ingress -n headlamp
kubectl describe ingress headlamp -n headlamp
```

### Permission Errors

1. **Verify ClusterRole binding**:
```bash
kubectl get clusterrole headlamp -o yaml
```

2. **Check specific permissions**:
```bash
# Test specific resource access
kubectl auth can-i get pods --all-namespaces \
  --as=system:serviceaccount:headlamp:headlamp
```

### Plugin Issues

1. **Check init container logs**:
```bash
kubectl logs -n headlamp -l app.kubernetes.io/name=headlamp -c kubescape-plugin --previous
```

2. **Verify plugin files**:
```bash
kubectl exec -n headlamp deployment/headlamp -- find /build/plugins -type f
```

### Performance Issues

1. **Check resource usage**:
```bash
kubectl top pod -n headlamp
```

2. **Review browser console**:
   - Open browser developer tools
   - Check for JavaScript errors
   - Monitor network requests

## Security Considerations

### RBAC Permissions
- Headlamp has cluster-admin level access
- Consider creating custom ClusterRole with limited permissions
- Use NetworkPolicies to restrict access

### Authentication
- Default deployment has no authentication
- Integrate with OAuth2 proxy or similar
- Consider using Keycloak for SSO

### Network Security
- Use HTTPS via ingress
- Implement network policies
- Consider IP whitelisting

### Best Practices
1. **Regular Updates**: Keep Headlamp and plugins updated
2. **Audit Access**: Monitor who accesses the dashboard
3. **Limit Permissions**: Use least-privilege RBAC if possible
4. **Secure Ingress**: Use TLS and authentication
5. **Monitor Usage**: Track API calls made by Headlamp

## Customization

### Adding Authentication

Example OAuth2 Proxy configuration:
```yaml
# oauth2-proxy deployment
- name: oauth2-proxy
  image: quay.io/oauth2-proxy/oauth2-proxy:latest
  args:
  - --provider=keycloak-oidc
  - --client-id=headlamp
  - --client-secret=$CLIENT_SECRET
  - --upstream=http://headlamp:80
  - --http-address=0.0.0.0:4180
```

### Custom Plugins

Create a plugin:
```javascript
// my-plugin/main.js
import { registerPlugin } from '@kinvolk/headlamp-plugin';

registerPlugin({
  name: 'my-plugin',
  version: '0.1.0',
  init: () => {
    console.log('My plugin initialized');
  }
});
```

### Theme Customization

Headlamp supports custom themes:
```javascript
// Custom theme configuration
window.HEADLAMP_CONFIG = {
  theme: {
    palette: {
      primary: {
        main: '#1976d2',
      },
    },
  },
};
```

## Monitoring

### Key Metrics
- Response time for API calls
- Memory usage (watch for leaks)
- Error rate in browser console
- Plugin loading time
- WebSocket connection stability

### Browser Performance
- Use browser developer tools
- Monitor memory usage
- Check network waterfall
- Profile JavaScript execution

## Integration Examples

### With Prometheus

View Prometheus metrics in Headlamp:
1. Install Prometheus plugin
2. Configure Prometheus endpoint
3. View metrics in dashboard

### With Grafana

Link to Grafana dashboards:
1. Add custom links in Headlamp
2. Configure deep linking
3. Pass context (namespace, pod, etc.)

### With Alerting

Integrate with alert systems:
1. Configure webhook notifications
2. Add alert annotations
3. Display in Headlamp UI

## Maintenance

### Regular Tasks

1. **Weekly**:
   - Review error logs
   - Check plugin updates
   - Monitor resource usage

2. **Monthly**:
   - Update Headlamp version
   - Review RBAC permissions
   - Audit access logs

3. **Quarterly**:
   - Security audit
   - Performance optimization
   - Plugin compatibility check

### Upgrade Procedure

1. **Check compatibility**:
   - Review changelog
   - Test in staging

2. **Update deployment**:
```yaml
image: ghcr.io/headlamp-k8s/headlamp:v0.34.0
```

3. **Verify functionality**:
   - Test core features
   - Check plugin compatibility

## Performance Optimization

### Client-Side
- Enable browser caching
- Use CDN for static assets
- Minimize plugin size
- Implement lazy loading

### Server-Side
- Increase resource limits if needed
- Use horizontal pod autoscaling
- Implement caching proxy
- Optimize API calls

### Network
- Enable compression
- Use HTTP/2
- Implement request batching
- Cache API responses

## Future Improvements

- [ ] Implement SSO with Keycloak
- [ ] Add custom branding
- [ ] Create cluster-specific plugins
- [ ] Add multi-cluster support
- [ ] Implement role-based UI
- [ ] Add dark mode
- [ ] Create mobile app
- [ ] Add CLI integration
- [ ] Implement audit logging
- [ ] Add cost management plugin
