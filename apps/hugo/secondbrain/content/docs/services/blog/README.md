# Hugo Blog Documentation Service

## Overview

The Hugo Blog service is a static site generator that serves as the central documentation hub for the Fako cluster. It automatically collects and organizes documentation from across the repository, presenting it in a searchable, user-friendly website. The service uses Hugo with automatic synchronization from GitHub.

## Key Features

- **Automatic Documentation Collection**: CronJob syncs docs every 6 hours
- **Static Site Generation**: Fast, secure Hugo-based site
- **GitHub Integration**: Pulls documentation directly from repository
- **Organized Structure**: Categorized documentation (services, guides, architecture)
- **Minimal Deployment**: Simple Hugo server with basic theme
- **Persistent Storage**: Documentation cached in PVC

## Architecture

### Components

1. **Deployment**: Single-replica Hugo server deployment
2. **Service**: ClusterIP service on port 80
3. **Ingress**: HTTPS access at `blog.fako-cluster.local`
4. **Storage**: 5Gi PersistentVolumeClaim for content
5. **ConfigMaps**: 
   - Documentation copy scripts
   - Hugo configuration (if customized)
6. **CronJob**: Automatic GitHub synchronization

### Resource Requirements

- **Memory**: 128Mi (request), 256Mi (limit)
- **CPU**: 100m (request), 500m (limit)
- **Storage**: 5Gi for Hugo site content

## Configuration

### Hugo Server Configuration

The deployment creates a minimal Hugo site on startup with:
- Basic theme structure
- Simple layouts (baseof, list, single, index)
- Homepage and documentation index
- Base URL: `https://blog.fako-cluster.local`

### Documentation Sync Configuration

The sync CronJob:
- **Schedule**: `0 */6 * * *` (every 6 hours)
- **Repository**: `https://github.com/lyzetam/fako-cluster.git`
- **Sync Strategy**: Shallow clone for efficiency

## Documentation Structure

```
/docs/                          # Central documentation directory
├── README.md                   # Main index
├── services/                   # Service-specific docs
│   ├── whisper/README.md
│   ├── ollama/README.md
│   ├── piper/README.md
│   └── ...
├── guides/                     # How-to guides
├── architecture/               # System design docs
├── infrastructure/             # Infrastructure docs
└── operations/                 # Operational procedures
```

## Usage

### Accessing the Blog

External access (with proper DNS/ingress):
```
https://blog.fako-cluster.local
```

Internal access:
```
http://hugo-blog.blog.svc.cluster.local
```

### Adding Documentation

1. **Create documentation** in the appropriate directory:
   ```bash
   # For a new service
   mkdir -p docs/services/myservice
   echo "# My Service" > docs/services/myservice/README.md
   ```

2. **Commit to GitHub**:
   ```bash
   git add docs/services/myservice/
   git commit -m "Add myservice documentation"
   git push
   ```

3. **Wait for sync** or trigger manually:
   ```bash
   kubectl create job --from=cronjob/sync-docs manual-sync-$(date +%s) -n blog
   ```

### Manual Documentation Sync

```bash
# Create one-off job from CronJob
kubectl create job --from=cronjob/sync-docs manual-sync -n blog

# Watch sync progress
kubectl logs -n blog -l job-name=manual-sync -f
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n blog

# View Hugo server logs
kubectl logs -n blog deployment/hugo-blog

# Check last sync job
kubectl get jobs -n blog | grep sync-docs
```

### Viewing Sync History

```bash
# List recent sync jobs
kubectl get jobs -n blog --sort-by=.metadata.creationTimestamp

# Check specific job logs
kubectl logs -n blog job/sync-docs-[job-id]
```

### Storage Management

```bash
# Check storage usage
kubectl exec -n blog deployment/hugo-blog -- df -h /site

# List documentation files
kubectl exec -n blog deployment/hugo-blog -- find /site/content -name "*.md" | wc -l
```

## Troubleshooting

### Blog Not Loading

1. **Check pod status**:
```bash
kubectl describe pod -n blog -l app.kubernetes.io/name=hugo-blog
```

2. **Verify Hugo is running**:
```bash
kubectl logs -n blog deployment/hugo-blog | grep "Web Server"
```

3. **Check ingress**:
```bash
kubectl get ingress -n blog
kubectl describe ingress hugo-blog -n blog
```

### Documentation Not Updating

1. **Check CronJob status**:
```bash
kubectl get cronjob sync-docs -n blog
```

2. **View last job execution**:
```bash
kubectl describe cronjob sync-docs -n blog | grep "Last Schedule Time"
```

3. **Check sync job logs**:
```bash
# Get latest job
JOB=$(kubectl get jobs -n blog --sort-by=.metadata.creationTimestamp | grep sync-docs | tail -1 | awk '{print $1}')
kubectl logs -n blog job/$JOB
```

### Sync Job Failures

1. **Network issues**:
```bash
# Test GitHub connectivity
kubectl run -n blog test-git --rm -it --image=alpine/git:latest -- \
  git ls-remote https://github.com/lyzetam/fako-cluster.git
```

2. **Storage issues**:
```bash
# Check PVC status
kubectl get pvc -n blog
kubectl describe pvc blog-content -n blog
```

3. **Permission issues**:
```bash
# Check file permissions
kubectl exec -n blog deployment/hugo-blog -- ls -la /site/content
```

## Customization

### Updating Hugo Theme

To use a proper Hugo theme instead of the minimal setup:

1. **Modify deployment**:
```yaml
# Add theme installation in deployment
git clone https://github.com/alex-shpak/hugo-book themes/book
echo 'theme = "book"' >> hugo.toml
```

2. **Configure theme settings**:
```toml
# hugo.toml additions
[params]
  BookTheme = 'light'
  BookToC = true
  BookRepo = 'https://github.com/lyzetam/fako-cluster'
  BookEditPath = 'edit/main'
```

### Adding Search Functionality

1. **Enable search in theme**
2. **Configure search index generation**
3. **Update layouts for search UI**

### Custom Styling

Add custom CSS:
```bash
# In deployment or ConfigMap
mkdir -p static/css
cat > static/css/custom.css <<'EOF'
/* Custom styles */
.content { max-width: 1200px; }
EOF
```

## Integration

### With CI/CD

Add documentation checks to your pipeline:
```yaml
# .github/workflows/docs.yml
- name: Check documentation
  run: |
    # Ensure all services have docs
    for service in apps/base/*/; do
      name=$(basename "$service")
      if [ ! -f "docs/services/$name/README.md" ]; then
        echo "Missing docs for $name"
        exit 1
      fi
    done
```

### With Monitoring

Monitor documentation site:
```yaml
# Uptime monitoring
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata:
  name: blog-probe
spec:
  targets:
    staticConfig:
      static:
      - http://hugo-blog.blog.svc.cluster.local
```

## Maintenance

### Regular Tasks

1. **Monitor sync job success rate**
2. **Check storage usage trends**
3. **Review Hugo server logs for errors**
4. **Update Hugo version periodically**

### Backup

Documentation is stored in Git, but for PVC backup:
```bash
# Create backup job
kubectl create job blog-backup -n blog \
  --from=cronjob/backup-blog-content
```

### Performance Optimization

1. **Enable Hugo caching**
2. **Optimize images in documentation**
3. **Use CDN for static assets**
4. **Configure appropriate cache headers**

## Security Considerations

- Hugo runs as non-root user (UID 1000)
- Read-only root filesystem where possible
- No external dependencies after build
- Static content reduces attack surface
- Git clone uses HTTPS (no SSH keys needed)

## Monitoring

### Key Metrics
- Sync job success/failure rate
- Documentation page count
- Storage usage percentage
- HTTP response times
- 404 error rate

### Alerts to Configure
- Sync job failures
- Storage >80% full
- Pod restart frequency
- Ingress certificate expiration

## Future Improvements

- [ ] Implement full Hugo Book theme
- [ ] Add documentation search functionality
- [ ] Create documentation quality checks
- [ ] Add analytics for popular pages
- [ ] Implement documentation versioning
- [ ] Add automatic broken link detection
- [ ] Create PDF export functionality
- [ ] Add multi-language support
- [ ] Implement comment system for feedback
- [ ] Add automatic diagram generation
