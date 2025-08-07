# Linkding - Bookmark Management Service

## Overview

Linkding is a self-hosted bookmark manager deployed in the Fako cluster. It provides a clean, minimal web interface for saving, organizing, and searching bookmarks. Linkding offers features like automatic title and description retrieval, tagging, full-text search, and bookmark archiving. It's designed as a privacy-focused alternative to commercial bookmark services, keeping all your data under your control.

## Key Features

- **Privacy-Focused**: Self-hosted with no external dependencies
- **Clean Interface**: Minimalist, fast web UI
- **Tagging System**: Organize bookmarks with tags
- **Full-Text Search**: Search titles, descriptions, and tags
- **Auto-Completion**: Title and description fetching
- **Archive Support**: Archive bookmarks with Wayback Machine
- **Import/Export**: Supports standard bookmark formats
- **REST API**: Programmatic access to bookmarks
- **Mobile-Friendly**: Responsive design for all devices

## Architecture

### Components

1. **Deployment**: Single-replica deployment
2. **Service**: ClusterIP service on port 9090
3. **Storage**: PersistentVolumeClaim for bookmark data
4. **Secret**: Environment variables for configuration
5. **Security Context**: Runs as www-data user (UID 33)

### Resource Requirements

- **Memory**: 128Mi (request), 256Mi (limit)
- **CPU**: 250m (request), 500m (limit)
- **Storage**: Persistent volume for database and assets

## Configuration

### Deployment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| Image | `sissbruecker/linkding:1.41.0` | Linkding version |
| Port | `9090` | Web interface port |
| User | `www-data (33)` | Run as non-root user |
| Data Path | `/etc/linkding/data` | Persistent data location |

### Environment Variables

Configuration via `linkding-container-env` secret:
- `LD_SUPERUSER_NAME`: Admin username
- `LD_SUPERUSER_PASSWORD`: Admin password
- `LD_DISABLE_REGISTRATION`: Disable public registration
- `LD_ENABLE_AUTH_PROXY`: Enable proxy authentication

## Usage

### Accessing Linkding

Internal access:
```
http://linkding.linkding.svc.cluster.local:9090
```

Port forwarding for local access:
```bash
kubectl port-forward -n linkding svc/linkding 9090:9090
# Access at http://localhost:9090
```

External access (requires ingress configuration)

### Initial Setup

1. **Access the web interface**
2. **Login** with superuser credentials from secret
3. **Configure settings**:
   - General settings
   - Import existing bookmarks
   - Set up integrations

### Basic Usage

#### Adding Bookmarks

1. **Quick Add**: Use the "+" button or Ctrl+D
2. **Enter URL**: Paste or type the URL
3. **Auto-fetch**: Title and description auto-populate
4. **Add tags**: Organize with tags
5. **Save**: Click save to add bookmark

#### Searching Bookmarks

- **Search bar**: Full-text search
- **Tag filter**: Click tags to filter
- **Advanced search**: Use operators:
  - `tag:important` - Search by tag
  - `!tag:read` - Exclude tag
  - Combine multiple filters

#### Browser Extension

Install the browser extension for easy bookmarking:
- Chrome/Firefox extensions available
- Configure with your instance URL
- One-click bookmark saving

### API Usage

Linkding provides a REST API:

```bash
# Get API token from settings

# List bookmarks
curl -H "Authorization: Token YOUR_TOKEN" \
  http://linkding.linkding.svc.cluster.local:9090/api/bookmarks/

# Add bookmark
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "title": "Example", "tag_names": ["test"]}' \
  http://linkding.linkding.svc.cluster.local:9090/api/bookmarks/
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n linkding

# View logs
kubectl logs -n linkding deployment/linkding

# Monitor resource usage
kubectl top pod -n linkding
```

### Backup and Restore

#### Export Bookmarks

1. **Via UI**:
   - Settings → Export
   - Choose format (HTML, JSON)
   - Download file

2. **Via API**:
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://linkding.linkding.svc.cluster.local:9090/api/bookmarks/ \
  > bookmarks-backup.json
```

#### Database Backup

```bash
# Backup SQLite database
kubectl exec -n linkding deployment/linkding -- \
  sqlite3 /etc/linkding/data/db.sqlite3 ".backup /tmp/backup.db"

# Copy to local
kubectl cp linkding/linkding-pod:/tmp/backup.db ./linkding-backup.db
```

### Import Bookmarks

1. **Via UI**:
   - Settings → Import
   - Upload HTML/JSON file
   - Choose import options

2. **From other services**:
   - Supports Netscape HTML format
   - Chrome/Firefox bookmarks
   - Pocket export

## Troubleshooting

### Cannot Access UI

1. **Check pod status**:
```bash
kubectl describe pod -n linkding -l app=linkding
```

2. **Verify service**:
```bash
kubectl get svc -n linkding
kubectl get endpoints -n linkding
```

3. **Check logs for errors**:
```bash
kubectl logs -n linkding deployment/linkding --tail=50
```

### Lost Admin Password

1. **Create new superuser**:
```bash
kubectl exec -it -n linkding deployment/linkding -- \
  python manage.py createsuperuser
```

2. **Or reset via environment**:
   - Update secret with new credentials
   - Restart pod

### Database Issues

1. **Check database integrity**:
```bash
kubectl exec -n linkding deployment/linkding -- \
  sqlite3 /etc/linkding/data/db.sqlite3 "PRAGMA integrity_check;"
```

2. **Repair database**:
```bash
# Backup first!
kubectl exec -n linkding deployment/linkding -- \
  sqlite3 /etc/linkding/data/db.sqlite3 "VACUUM;"
```

### Storage Full

1. **Check usage**:
```bash
kubectl exec -n linkding deployment/linkding -- \
  df -h /etc/linkding/data
```

2. **Clean up**:
   - Remove archived pages if enabled
   - Delete old backups
   - Compact database

## Security Considerations

### Authentication
- Strong admin password required
- Optional: Disable self-registration
- API tokens for programmatic access
- Consider proxy authentication with Keycloak

### Network Security
- Internal-only by default
- Use HTTPS ingress for external access
- Implement network policies
- Rate limiting recommended

### Data Privacy
- All data stored locally
- No external services by default
- Optional archive integration
- Regular backups recommended

### Best Practices
1. **Disable registration**: Prevent unauthorized accounts
2. **Use strong passwords**: Enforce password policy
3. **Regular backups**: Automate backup process
4. **Monitor access**: Check logs for suspicious activity
5. **Update regularly**: Keep Linkding updated

## Customization

### Theme and Appearance

Linkding supports custom CSS:
1. Settings → General
2. Add custom CSS
3. Examples:
```css
/* Dark theme adjustments */
:root {
  --primary-color: #1976d2;
  --background-color: #121212;
}
```

### Integration Options

#### Wayback Machine
Enable bookmark archiving:
- Settings → Integrations
- Enable Internet Archive integration
- Automatic snapshot creation

#### Browser Extensions
Configure extensions:
- Set instance URL
- Configure shortcuts
- Customize behavior

## Performance Optimization

### Database
- Regular VACUUM operations
- Index optimization
- Query performance monitoring

### Caching
- Enable browser caching
- Use CDN for static assets
- Optimize favicon fetching

### Resource Tuning
```yaml
# For larger deployments
resources:
  requests:
    memory: "256Mi"
    cpu: "500m"
  limits:
    memory: "512Mi"
    cpu: "1000m"
```

## Monitoring

### Key Metrics
- Response times
- Database size growth
- Failed URL fetches
- User activity
- Storage usage

### Health Checks

Add liveness/readiness probes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /
    port: 9090
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor disk usage
   - Check for failed fetches

2. **Weekly**:
   - Backup database
   - Review user activity
   - Clean orphaned data

3. **Monthly**:
   - Update Linkding
   - Optimize database
   - Review security logs

### Upgrade Procedure

1. **Backup data**:
```bash
kubectl exec -n linkding deployment/linkding -- \
  tar -czf /tmp/backup.tar.gz /etc/linkding/data
```

2. **Update deployment**:
```yaml
image: sissbruecker/linkding:1.42.0
```

3. **Monitor migration**:
```bash
kubectl logs -n linkding deployment/linkding -f
```

## Integration Examples

### With N8N

Create automated workflows:
1. Monitor RSS feeds
2. Auto-bookmark matching articles
3. Tag based on content
4. Send notifications

### With Scripts

```python
import requests

# Linkding API client
class LinkdingClient:
    def __init__(self, url, token):
        self.url = url
        self.headers = {"Authorization": f"Token {token}"}
    
    def add_bookmark(self, url, title, tags):
        data = {
            "url": url,
            "title": title,
            "tag_names": tags
        }
        return requests.post(
            f"{self.url}/api/bookmarks/",
            json=data,
            headers=self.headers
        )
```

## Future Improvements

- [ ] Implement SSO with Keycloak
- [ ] Add PostgreSQL backend option
- [ ] Create mobile app
- [ ] Add collaborative features
- [ ] Implement bookmark sharing
- [ ] Add full-page archiving
- [ ] Create browser sync
- [ ] Add AI-powered tagging
- [ ] Implement bookmark recommendations
- [ ] Add analytics dashboard
