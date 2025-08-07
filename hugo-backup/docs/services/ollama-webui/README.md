# Ollama WebUI - Test Instance of Open WebUI

## Overview

Ollama WebUI is a test/staging deployment of Open WebUI in the Fako cluster. Despite its name, this service actually uses the Open WebUI image and is configured to connect to GPUStack (not Ollama) as its AI backend. It serves as a testing environment for new configurations, model testing, and user onboarding before changes are promoted to the production Open WebUI instance. This separation allows for safe experimentation without affecting production users.

## Key Features

- **Test Environment**: Isolated instance for testing and development
- **Same UI as Production**: Uses identical Open WebUI interface
- **GPUStack Backend**: Configured for OpenAI-compatible API (not Ollama)
- **User Registration**: Signup enabled for testing (unlike production)
- **Model Testing**: Test new models before production deployment
- **Configuration Testing**: Validate settings before production
- **Same Resource Allocation**: Mirrors production resource requirements

## Architecture

### Components

1. **Deployment**: Single-replica stateful deployment
2. **Service**: ClusterIP service on port 8080
3. **Ingress**: HTTPS access for test users
4. **Storage**: Separate PVC from production (`ollama-webui-data`)
5. **ConfigMap**: Test-specific configuration
6. **External Secrets**: Shared GPUStack credentials from AWS

### Resource Requirements

- **Memory**: 3Gi (request), 6Gi (limit)
- **CPU**: 1.5 cores (request), 3 cores (limit)
- **Storage**: Isolated persistent volume

## Configuration

### Key Differences from Production

| Setting | Test (ollama-webui) | Production (open-webui) |
|---------|-------------------|----------------------|
| `ENABLE_SIGNUP` | `true` | `false` |
| `WEBUI_NAME` | `HomeLab AI (GPUStack) - Test` | `HomeLab AI (GPUStack) - Production` |
| Database | Separate SQLite | Separate SQLite |
| Namespace | `ollama-webui` | `open-webui` |

### Backend Configuration

- **AI Backend**: GPUStack (OpenAI-compatible)
- **Ollama API**: Disabled (despite the service name)
- **Models**: Same as production (`gemma-3-27b-it,glm4-0414`)

## Usage

### Accessing Test Instance

Internal access:
```
http://ollama-webui.ollama-webui.svc.cluster.local:8080
```

Port forwarding:
```bash
kubectl port-forward -n ollama-webui svc/ollama-webui 8081:8080
# Access at http://localhost:8081
```

External access (if ingress configured):
```
https://test-ai.your-domain.com
```

### Test Environment Use Cases

1. **New User Testing**:
   - Enable signup for test accounts
   - Test user onboarding flow
   - Validate permissions

2. **Model Testing**:
   - Test new models before production
   - Compare model performance
   - Validate model compatibility

3. **Configuration Changes**:
   - Test new environment variables
   - Validate API endpoints
   - Test resource limits

4. **Feature Testing**:
   - Enable experimental features
   - Test integrations
   - Validate workflows

### Creating Test Accounts

Since signup is enabled:
1. Navigate to test instance
2. Click "Sign Up"
3. Create test account
4. Test functionality

## Operations

### Syncing with Production

Copy production data for testing:
```bash
# Export from production
kubectl exec -n open-webui deployment/open-webui -- \
  cp /app/backend/data/webui.db /tmp/prod-backup.db

# Copy to local
kubectl cp open-webui/open-webui-pod:/tmp/prod-backup.db ./prod-backup.db

# Import to test
kubectl cp ./prod-backup.db ollama-webui/ollama-webui-pod:/tmp/test-import.db

# Replace test database (CAUTION: backs up existing first)
kubectl exec -n ollama-webui deployment/ollama-webui -- bash -c \
  "cp /app/backend/data/webui.db /app/backend/data/webui.db.bak && \
   cp /tmp/test-import.db /app/backend/data/webui.db"
```

### Promoting Changes

After testing, promote configurations:
```bash
# Compare configurations
diff -u <(kubectl get cm ollama-webui-configmap -n ollama-webui -o yaml) \
        <(kubectl get cm open-webui-configmap -n open-webui -o yaml)

# Apply tested changes to production
kubectl get cm ollama-webui-configmap -n ollama-webui -o yaml | \
  sed 's/ollama-webui/open-webui/g' | \
  sed 's/Test/Production/g' | \
  sed 's/ENABLE_SIGNUP: "true"/ENABLE_SIGNUP: "false"/g' | \
  kubectl apply -f -
```

### Monitoring Test Usage

```bash
# Check active users
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  sqlite3 /app/backend/data/webui.db \
  "SELECT COUNT(*) as total_users FROM users;"

# Recent activity
kubectl logs -n ollama-webui deployment/ollama-webui --tail=100
```

## Troubleshooting

### Database Issues

1. **Reset test database**:
```bash
# Backup current
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  cp /app/backend/data/webui.db /app/backend/data/webui.db.backup

# Create fresh database
kubectl delete pod -n ollama-webui -l app=ollama-webui
```

2. **Check database size**:
```bash
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  ls -lh /app/backend/data/
```

### Configuration Sync Issues

1. **Verify secrets**:
```bash
# Compare secrets between environments
kubectl get secrets -n ollama-webui
kubectl get secrets -n open-webui
```

2. **Check external secrets**:
```bash
kubectl describe externalsecret -n ollama-webui
```

### Performance Testing

1. **Load testing**:
```bash
# Monitor resource usage during tests
kubectl top pod -n ollama-webui -l app=ollama-webui
```

2. **Response time testing**:
```bash
# Time API responses
time curl -s http://ollama-webui.ollama-webui.svc.cluster.local:8080/api/health
```

## Security Considerations

### Test Data Isolation
- Separate database from production
- Isolated namespace
- No production data access

### User Management
- Test accounts should be clearly marked
- Regular cleanup of test users
- Different admin credentials

### API Keys
- Shared GPUStack credentials (be cautious)
- Monitor API usage from test
- Consider separate API limits

### Best Practices
1. **Clear naming**: Label test users clearly
2. **Regular cleanup**: Delete old test data
3. **Access control**: Limit who can access test
4. **Monitoring**: Track test environment usage
5. **Documentation**: Document test scenarios

## Test Scenarios

### Model Evaluation

Test new model configurations:
```yaml
# Test configmap
DEFAULT_MODELS: "new-model-1,new-model-2,existing-model"
MODEL_FILTER_ENABLED: "true"
MODEL_FILTER_LIST: "new-model-1,new-model-2"
```

### Performance Testing

Stress test configurations:
```yaml
# Increase timeouts for testing
OPENAI_REQUEST_TIMEOUT: "1200"  # 20 minutes
WEBUI_SESSION_LIFETIME: "3600"  # 1 hour for quick testing
```

### Feature Flags

Test experimental features:
```yaml
# Enable experimental features
ENABLE_RAG: "true"
ENABLE_IMAGE_GENERATION: "true"
ENABLE_COMMUNITY_SHARING: "true"
```

## Integration Testing

### With GPUStack

Test endpoint changes:
```bash
# Update endpoint secret
kubectl edit secret ollama-endpoints -n ollama-webui

# Test connection
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  curl -s $OPENAI_API_BASE_URL/models
```

### With Monitoring

Test metrics collection:
```yaml
# Add metrics endpoint
ENABLE_METRICS: "true"
METRICS_PORT: "9090"
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor test usage
   - Check for errors
   - Clean up test conversations

2. **Weekly**:
   - Review test accounts
   - Analyze test results
   - Plan production updates

3. **Monthly**:
   - Reset test environment
   - Update test scenarios
   - Sync with production versions

### Test Data Management

Clean old test data:
```bash
# Delete old conversations
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  sqlite3 /app/backend/data/webui.db \
  "DELETE FROM conversations WHERE created_at < datetime('now', '-7 days');"

# Vacuum database
kubectl exec -n ollama-webui deployment/ollama-webui -- \
  sqlite3 /app/backend/data/webui.db "VACUUM;"
```

### Version Management

Keep test in sync with production:
```bash
# Check versions
kubectl get deployment -n ollama-webui ollama-webui -o yaml | grep image:
kubectl get deployment -n open-webui open-webui -o yaml | grep image:

# Update test to match production
kubectl set image deployment/ollama-webui ollama-webui=ghcr.io/open-webui/open-webui:v0.6.19 \
  -n ollama-webui
```

## Migration Path

### To Production

1. **Validate changes**: Test thoroughly
2. **Document changes**: Create change log
3. **Backup production**: Before applying
4. **Apply changes**: During maintenance window
5. **Verify**: Test production post-change

### Deprecation Plan

Consider renaming to avoid confusion:
```bash
# Future: Rename to test-webui
kubectl create namespace test-webui
# Migrate resources
# Update documentation
```

## Future Improvements

- [ ] Rename service to clarify it's not Ollama-specific
- [ ] Implement automated test scenarios
- [ ] Add A/B testing capabilities
- [ ] Create test data generators
- [ ] Implement automated promotion pipeline
- [ ] Add performance benchmarking
- [ ] Create test result dashboards
- [ ] Implement feature flag system
- [ ] Add automated regression testing
- [ ] Create staging environment between test and prod
