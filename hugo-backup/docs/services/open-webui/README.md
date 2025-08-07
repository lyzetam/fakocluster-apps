# Open WebUI - AI Chat Interface

## Overview

Open WebUI is a feature-rich, user-friendly web interface for AI language models deployed in the Fako cluster. It provides a ChatGPT-like experience with support for multiple AI backends. This deployment is configured to use GPUStack as the primary AI backend, providing access to various open-source language models through an OpenAI-compatible API.

## Key Features

- **Modern Chat Interface**: Clean, responsive UI similar to ChatGPT
- **Multi-Model Support**: Access multiple AI models from GPUStack
- **User Management**: Built-in authentication and user roles
- **Conversation History**: Persistent chat storage with SQLite
- **Model Switching**: Easy switching between available models
- **Custom System Prompts**: Create and save custom prompts
- **Dark/Light Mode**: Theme switching for user preference
- **Mobile Responsive**: Works seamlessly on all devices

## Architecture

### Components

1. **Deployment**: Single-replica stateful deployment
2. **Service**: ClusterIP service on port 8080
3. **Ingress**: HTTPS access for external users
4. **Storage**: PersistentVolumeClaim for SQLite database and user data
5. **ConfigMap**: Application configuration
6. **External Secrets**: API keys and endpoints from AWS Secrets Manager

### Resource Requirements

- **Memory**: 3Gi (request), 6Gi (limit)
- **CPU**: 1.5 cores (request), 3 cores (limit)
- **Storage**: Persistent volume for database and uploads

## Configuration

### Application Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `ENABLE_OLLAMA_API` | `false` | Ollama disabled, using GPUStack |
| `ENABLE_OPENAI_API` | `true` | OpenAI-compatible API enabled |
| `WEBUI_NAME` | `HomeLab AI (GPUStack) - Production` | Instance name |
| `WEBUI_AUTH` | `true` | Authentication enabled |
| `ENABLE_SIGNUP` | `false` | New signups disabled |
| `DEFAULT_MODELS` | `gemma-3-27b-it,glm4-0414` | Available models |
| `BYPASS_MODEL_ACCESS_CONTROL` | `true` | All models visible to all users |

### Backend Configuration

- **AI Backend**: GPUStack (OpenAI-compatible)
- **Database**: SQLite at `/app/backend/data/webui.db`
- **Session Lifetime**: 30 days (2592000 seconds)
- **Request Timeout**: 10 minutes for large models

## Usage

### Accessing Open WebUI

External access:
```
https://openwebui.your-domain.com
```

Internal access:
```
http://open-webui.open-webui.svc.cluster.local:8080
```

Port forwarding for local access:
```bash
kubectl port-forward -n open-webui svc/open-webui 8080:8080
# Access at http://localhost:8080
```

### User Accounts

Since signup is disabled and production data was migrated:
1. Use existing credentials from production
2. Admin can create new accounts via UI
3. Password reset requires admin intervention

### Basic Chat Usage

1. **Login** with your credentials
2. **Select a model** from the dropdown:
   - `gemma-3-27b-it`: Google's Gemma model
   - `glm4-0414`: GLM-4 model
3. **Start chatting**: Type your message and press Enter
4. **Switch models**: Change mid-conversation if needed

### Advanced Features

#### Custom System Prompts
1. Click on model settings
2. Add system prompt
3. Save as preset for reuse

#### Conversation Management
- **New Chat**: Click "+" or Ctrl+N
- **Search History**: Use search bar
- **Export Chat**: Download as JSON/Markdown
- **Delete Chat**: Right-click → Delete

#### User Preferences
- **Theme**: Toggle dark/light mode
- **Language**: Multiple languages supported
- **Font Size**: Adjustable for accessibility

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n open-webui

# View logs
kubectl logs -n open-webui deployment/open-webui

# Monitor startup
kubectl logs -n open-webui deployment/open-webui -f
```

### Database Management

#### Backup Database
```bash
# Create backup
kubectl exec -n open-webui deployment/open-webui -- \
  cp /app/backend/data/webui.db /app/backend/data/webui.db.backup

# Copy to local
kubectl cp open-webui/open-webui-pod:/app/backend/data/webui.db.backup ./webui-backup.db
```

#### View Database Info
```bash
# Check database size
kubectl exec -n open-webui deployment/open-webui -- \
  ls -lh /app/backend/data/webui.db

# Count users
kubectl exec -n open-webui deployment/open-webui -- \
  sqlite3 /app/backend/data/webui.db "SELECT COUNT(*) FROM users;"
```

### User Management

#### Create Admin User (via CLI)
```bash
kubectl exec -it -n open-webui deployment/open-webui -- \
  python -c "
from apps.webui.models.users import Users
Users.create_user({
  'email': 'admin@example.com',
  'name': 'Admin',
  'password': 'secure_password',
  'role': 'admin'
})
"
```

#### Reset User Password
```bash
# Connect to pod and use Python console
kubectl exec -it -n open-webui deployment/open-webui -- python
```

## Troubleshooting

### Cannot Login

1. **Check authentication is enabled**:
```bash
kubectl get cm open-webui-configmap -n open-webui -o yaml | grep WEBUI_AUTH
```

2. **Verify database exists**:
```bash
kubectl exec -n open-webui deployment/open-webui -- \
  ls -la /app/backend/data/
```

3. **Check for migration issues**:
```bash
kubectl logs -n open-webui deployment/open-webui | grep -i migration
```

### Models Not Showing

1. **Verify GPUStack connection**:
```bash
# Check secrets
kubectl get secret -n open-webui ollama-endpoints -o yaml
kubectl get secret -n open-webui gpustack-credentials -o yaml
```

2. **Test API endpoint**:
```bash
kubectl exec -n open-webui deployment/open-webui -- \
  curl -s http://gpustack.gpustack.svc.cluster.local/v1/models
```

3. **Check model configuration**:
```bash
kubectl get cm open-webui-configmap -n open-webui -o yaml | grep DEFAULT_MODELS
```

### Performance Issues

1. **Check resource usage**:
```bash
kubectl top pod -n open-webui
```

2. **Monitor response times**:
   - Enable debug logging: `WEBUI_LOG_LEVEL: "DEBUG"`
   - Check browser console for API timings

3. **Database optimization**:
```bash
# Vacuum database
kubectl exec -n open-webui deployment/open-webui -- \
  sqlite3 /app/backend/data/webui.db "VACUUM;"
```

### Chat History Issues

1. **Check storage**:
```bash
kubectl get pvc -n open-webui
kubectl exec -n open-webui deployment/open-webui -- df -h /app/backend/data
```

2. **Verify permissions**:
```bash
kubectl exec -n open-webui deployment/open-webui -- \
  ls -la /app/backend/data/
```

## Security Considerations

### Authentication & Authorization
- Authentication required by default
- Admin and user roles supported
- No OAuth/SSO in default config
- Session tokens stored in SQLite

### Data Privacy
- All conversations stored locally
- No telemetry to external services
- User data never leaves cluster

### Network Security
- Use HTTPS via ingress
- Implement network policies
- Restrict GPUStack access

### Best Practices
1. **Regular backups**: Backup SQLite database
2. **Strong passwords**: Enforce password policy
3. **Audit access**: Monitor login attempts
4. **Update regularly**: Keep Open WebUI updated
5. **Limit model access**: Control which models are available

## Integration

### With GPUStack

Current configuration uses GPUStack as backend:
```yaml
ENABLE_OPENAI_API: "true"
# API URLs loaded from AWS Secrets Manager
# API keys loaded from AWS Secrets Manager
```

### With Keycloak (Future)

For SSO integration:
```yaml
# OAuth2 configuration
WEBUI_AUTH_TYPE: "oauth2"
OAUTH2_PROVIDER_URL: "https://auth.landryzetam.net"
OAUTH2_CLIENT_ID: "open-webui"
```

### With Monitoring

Add Prometheus metrics:
```yaml
ENABLE_METRICS: "true"
METRICS_PORT: "9090"
```

## Performance Optimization

### Frontend
- Enable browser caching
- Use CDN for static assets
- Minimize JavaScript bundles
- Lazy load conversations

### Backend
- Optimize SQLite settings
- Implement connection pooling
- Cache model responses
- Use async processing

### Model Inference
- Select appropriate model sizes
- Adjust timeout settings
- Implement request queuing
- Monitor GPU utilization

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor active users
   - Check error logs
   - Review resource usage

2. **Weekly**:
   - Backup database
   - Clean old sessions
   - Check storage usage

3. **Monthly**:
   - Update Open WebUI
   - Audit user accounts
   - Review model usage

### Database Maintenance

```bash
# Analyze database
kubectl exec -n open-webui deployment/open-webui -- \
  sqlite3 /app/backend/data/webui.db "ANALYZE;"

# Check integrity
kubectl exec -n open-webui deployment/open-webui -- \
  sqlite3 /app/backend/data/webui.db "PRAGMA integrity_check;"
```

### Upgrade Procedure

1. **Backup data**:
```bash
kubectl create job -n open-webui backup-$(date +%s) \
  --from=cronjob/webui-backup
```

2. **Update image**:
```yaml
image: ghcr.io/open-webui/open-webui:v0.6.19
```

3. **Monitor migration**:
```bash
kubectl logs -n open-webui deployment/open-webui -f
```

## Advanced Configuration

### Custom Models

Add new models to GPUStack and update:
```yaml
DEFAULT_MODELS: "model1,model2,model3"
```

### RAG (Retrieval Augmented Generation)

Enable when supported:
```yaml
ENABLE_RAG: "true"
RAG_EMBEDDING_MODEL: "all-MiniLM-L6-v2"
```

### Multi-Language Support

Configure UI languages:
```yaml
DEFAULT_LOCALE: "en-US"
AVAILABLE_LOCALES: "en-US,es-ES,fr-FR"
```

## Future Improvements

- [ ] Implement SSO with Keycloak
- [ ] Add PostgreSQL backend option
- [ ] Enable RAG with vector database
- [ ] Add model usage analytics
- [ ] Implement conversation sharing
- [ ] Add voice input/output
- [ ] Create mobile app
- [ ] Add collaborative features
- [ ] Implement model fine-tuning UI
- [ ] Add cost tracking per user
