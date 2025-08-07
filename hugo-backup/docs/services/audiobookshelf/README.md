# Audiobookshelf - Audiobook and Podcast Server

## Overview

Audiobookshelf is a self-hosted audiobook and podcast server deployed in the Fako cluster. It provides a comprehensive media management system with features like automatic metadata fetching, progress syncing across devices, and a beautiful web interface. Audiobookshelf supports various audio formats and offers mobile apps for iOS and Android, making it a complete solution for managing and enjoying your audio library.

## Key Features

- **Multi-Format Support**: MP3, M4A, M4B, FLAC, OGG, and more
- **Automatic Metadata**: Fetches cover art, descriptions, and metadata
- **Progress Sync**: Syncs playback position across all devices
- **Mobile Apps**: Native iOS and Android applications
- **Multi-User**: Support for multiple users with individual progress
- **Series Management**: Organize books by series and authors
- **Podcast Support**: Subscribe and manage podcast feeds
- **Sleep Timer**: Built-in sleep timer for bedtime listening
- **Variable Playback Speed**: Adjust playback speed to preference

## Architecture

### Components

1. **Deployment**: Single-replica deployment
2. **Service**: ClusterIP service on port 3005
3. **Storage**: Three PersistentVolumeClaims:
   - Config: Application configuration and database
   - Metadata: Cover images and cached metadata
   - Audiobooks: Media library storage
4. **ConfigMap**: Basic configuration settings
5. **Security Context**: Runs as user 1000

### Resource Requirements

- **Memory**: 512Mi (request), 1Gi (limit)
- **CPU**: 250m (request), 1000m (limit)
- **Storage**: 
  - Config volume for database
  - Metadata volume for images/cache
  - Audiobooks volume for media files

## Configuration

### Deployment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| Image | `ghcr.io/advplyr/audiobookshelf:2.26.0` | Audiobookshelf version |
| Port | `3005` | Web interface port |
| User/Group | `1000` | Non-root user |
| Volumes | 3 mounts | Config, metadata, and media |

### Volume Mounts

- `/config`: Database and configuration files
- `/metadata`: Cover art and metadata cache
- `/audiobooks`: Media library root directory

## Usage

### Accessing Audiobookshelf

Internal access:
```
http://audiobookshelf.audiobookshelf.svc.cluster.local:3005
```

Port forwarding for local access:
```bash
kubectl port-forward -n audiobookshelf svc/audiobookshelf 3005:3005
# Access at http://localhost:3005
```

External access (requires ingress configuration)

### Initial Setup

1. **Access the web interface**
2. **Create admin account** on first visit
3. **Configure library folders**:
   - Add audiobook folders
   - Add podcast folders
4. **Set up users** if needed
5. **Configure server settings**

### Library Management

#### Adding Books

1. **Upload files** to the audiobooks volume:
   - Via web interface upload
   - Direct file copy to PVC
   - Network share mount

2. **Organize structure**:
   ```
   /audiobooks/
   ├── Author Name/
   │   ├── Book Title/
   │   │   ├── track01.mp3
   │   │   ├── track02.mp3
   │   │   └── cover.jpg
   │   └── Another Book/
   └── Podcasts/
   ```

3. **Scan library**:
   - Settings → Libraries → Scan

#### Metadata Management

- **Automatic matching**: Uses Google Books, OpenLibrary
- **Manual editing**: Edit any metadata field
- **Cover art**: Auto-fetch or upload custom
- **Series grouping**: Organize books in series

### Mobile App Setup

1. **Install app** from App Store/Play Store
2. **Server connection**:
   - Enter server URL
   - Use external URL or VPN
3. **Login** with your credentials
4. **Download** books for offline listening

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n audiobookshelf

# View logs
kubectl logs -n audiobookshelf deployment/audiobookshelf

# Monitor resource usage
kubectl top pod -n audiobookshelf
```

### Backup and Restore

#### Database Backup

```bash
# Backup SQLite database
kubectl exec -n audiobookshelf deployment/audiobookshelf -- \
  cp /config/absdatabase.sqlite /config/absdatabase.sqlite.backup

# Copy to local
kubectl cp audiobookshelf/audiobookshelf-pod:/config/absdatabase.sqlite.backup \
  ./audiobookshelf-backup.sqlite
```

#### Full Backup

```bash
# Create tarball of config
kubectl exec -n audiobookshelf deployment/audiobookshelf -- \
  tar -czf /tmp/config-backup.tar.gz /config

# Copy locally
kubectl cp audiobookshelf/audiobookshelf-pod:/tmp/config-backup.tar.gz \
  ./audiobookshelf-config-backup.tar.gz
```

### Library Maintenance

#### Scan for New Books
- Via UI: Settings → Libraries → Scan
- Force rescan for metadata updates

#### Clean Missing Files
- Remove entries for deleted files
- Update file paths if moved

#### Manage Storage
```bash
# Check storage usage
kubectl exec -n audiobookshelf deployment/audiobookshelf -- \
  df -h /audiobooks /metadata /config
```

## Troubleshooting

### Cannot Access Web Interface

1. **Check pod status**:
```bash
kubectl describe pod -n audiobookshelf -l app=audiobookshelf
```

2. **Verify service**:
```bash
kubectl get endpoints -n audiobookshelf
```

3. **Check logs**:
```bash
kubectl logs -n audiobookshelf deployment/audiobookshelf --tail=100
```

### Playback Issues

1. **Check file format**: Ensure supported audio format
2. **Verify permissions**: Files readable by user 1000
3. **Browser compatibility**: Try different browser
4. **Network speed**: Check bandwidth for streaming

### Metadata Not Fetching

1. **Internet access**: Verify pod can reach external APIs
2. **API limits**: Some providers have rate limits
3. **Manual match**: Try different search terms
4. **Custom metadata**: Add manually if needed

### Mobile App Connection Issues

1. **Server URL**: Ensure correct external URL
2. **SSL/TLS**: Valid certificate for HTTPS
3. **Firewall**: Port accessible from internet
4. **Authentication**: Correct username/password

## Security Considerations

### Authentication
- Local user accounts with bcrypt passwords
- No default credentials
- Session-based authentication
- API tokens for mobile apps

### Network Security
- Use HTTPS for external access
- VPN for internal network access
- Implement firewall rules
- Rate limiting on API endpoints

### Data Privacy
- All data stored locally
- No cloud dependencies
- User listening data private
- Optional anonymous statistics

### Best Practices
1. **Strong passwords**: Enforce password requirements
2. **HTTPS only**: Use TLS for external access
3. **Regular updates**: Keep Audiobookshelf updated
4. **Backup data**: Regular automated backups
5. **Monitor access**: Check logs for unusual activity

## Performance Optimization

### Transcoding
- Pre-transcode if needed
- Optimize audio bitrates
- Use efficient codecs

### Caching
- Metadata cache in separate volume
- Browser cache for cover art
- CDN for static assets

### Database
- Regular VACUUM operations
- Index optimization
- Query performance monitoring

### Resource Scaling
```yaml
# For larger libraries
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Monitoring

### Key Metrics
- Active users/sessions
- Playback statistics
- Storage usage growth
- API response times
- Transcoding load

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /ping
    port: 3005
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ping
    port: 3005
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Integration Examples

### With File Sync

Sync audiobooks from NAS:
```yaml
# Add NFS volume mount
volumes:
- name: nas-audiobooks
  nfs:
    server: nas.local
    path: /audiobooks
```

### Reverse Proxy Setup

Nginx configuration:
```nginx
location /audiobooks/ {
    proxy_pass http://audiobookshelf:3005/;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;
    
    # WebSocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Backup Automation

```bash
#!/bin/bash
# backup-audiobookshelf.sh

NAMESPACE="audiobookshelf"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup database
kubectl exec -n $NAMESPACE deployment/audiobookshelf -- \
  sqlite3 /config/absdatabase.sqlite ".backup /tmp/backup.db"

# Copy to persistent backup location
kubectl cp $NAMESPACE/audiobookshelf-pod:/tmp/backup.db \
  /backups/audiobookshelf/db_$TIMESTAMP.sqlite
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor disk usage
   - Check failed uploads
   - Review error logs

2. **Weekly**:
   - Backup database
   - Update metadata
   - Clean temp files

3. **Monthly**:
   - Update Audiobookshelf
   - Optimize database
   - Review user activity

### Upgrade Procedure

1. **Backup everything**:
   - Database
   - Configuration
   - Cover art cache

2. **Update deployment**:
```yaml
image: ghcr.io/advplyr/audiobookshelf:2.27.0
```

3. **Monitor startup**:
```bash
kubectl logs -n audiobookshelf deployment/audiobookshelf -f
```

## Future Improvements

- [ ] Implement SSO with Keycloak
- [ ] Add automated metadata enrichment
- [ ] Create backup CronJob
- [ ] Add Prometheus metrics
- [ ] Implement CDN for cover art
- [ ] Add support for comics/ebooks
- [ ] Create recommendation engine
- [ ] Add social features
- [ ] Implement bandwidth limiting
- [ ] Add parental controls
