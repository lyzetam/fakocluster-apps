# wger - Fitness and Workout Manager

## Overview

wger (Workout Manager) is a free, open-source fitness and workout tracking application deployed in the Fako cluster. It provides comprehensive features for managing workouts, tracking nutrition, monitoring body weight, and creating exercise routines. The application includes a large exercise database with images and videos, making it an excellent self-hosted alternative to commercial fitness apps. It's accessible via the web interface and offers both registered user accounts and guest access.

## Key Features

- **Workout Management**: Create and track custom workout routines
- **Exercise Database**: Large database with images and videos
- **Nutrition Tracking**: Log meals and track calories/macros
- **Weight Tracking**: Monitor body weight progress over time
- **Multi-Language**: Support for multiple languages
- **REST API**: Full API for mobile apps and integrations
- **Guest Access**: Try before registering
- **PDF Export**: Generate workout plans as PDFs
- **Exercise Sync**: Automatic sync of exercise database

## Architecture

### Components

1. **Helm Release**: Deployed via Flux Helm controller
2. **Django Backend**: Python-based web framework
3. **PostgreSQL Database**: Uses cluster's PostgreSQL
4. **Redis Cache**: For performance optimization
5. **Celery Workers**: Background task processing
6. **nginx**: Web server and static file serving
7. **Persistent Storage**: NFS for media files

### Resource Requirements

- **Django App**: 256Mi RAM (request), 1Gi (limit)
- **Celery**: 256Mi RAM (request), 512Mi (limit)
- **CPU**: 250m-1000m for app, 100m-500m for Celery
- **Storage**: 10Gi for media, 5Gi for Redis

## Configuration

### Application Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `WGER_ALLOW_REGISTRATION` | `True` | Open registration |
| `WGER_ALLOW_GUEST_USERS` | `True` | Guest access enabled |
| `DJANGO_DEBUG` | `False` | Production mode |
| `EXERCISE_CACHE_TTL` | `86400` | 24-hour cache |
| `WGER_USE_GUNICORN` | `True` | Production server |

### Infrastructure

- **Database**: External PostgreSQL cluster
- **Cache**: Redis with 5Gi storage
- **Ingress**: `trackit.landryzetam.net`
- **Storage Class**: `nfs-csi-v2`

## Usage

### Accessing wger

External access:
```
https://trackit.landryzetam.net
```

Internal access:
```
http://wger.wger.svc.cluster.local:8000
```

### Getting Started

1. **Visit the site**: Navigate to the URL
2. **Choose access type**:
   - Register new account
   - Use guest account
   - Login with existing account
3. **Create first workout**:
   - Browse exercise database
   - Create workout routine
   - Add exercises with sets/reps
4. **Track progress**:
   - Log workouts
   - Track weight
   - Monitor nutrition

### Mobile Access

- Responsive web design works on all devices
- REST API available for custom apps
- Progressive Web App (PWA) support

## Exercise Management

### Database Features

- **Automatic Sync**: Celery syncs exercises daily
- **Images & Videos**: Visual exercise guides
- **Categories**: Organized by muscle groups
- **Equipment**: Filter by available equipment
- **Custom Exercises**: Add your own

### Creating Workouts

1. **Templates**: Use pre-made routines
2. **Custom Plans**: Build from scratch
3. **Scheduling**: Set workout days
4. **Logging**: Track completed sets
5. **Progress**: View strength gains

## Operations

### Database Initialization

The database is initialized via job:
```bash
# Check init job status
kubectl get job wger-db-init -n wger

# View initialization logs
kubectl logs -n wger job/wger-db-init
```

### Managing Users

Django admin interface:
```bash
# Create superuser
kubectl exec -it -n wger deployment/wger -- \
  python manage.py createsuperuser

# Access admin at /admin
```

### Backup Procedures

#### Database Backup
```bash
# Backup wger database
kubectl exec -n postgres postgres-cluster-1 -- \
  pg_dump -U postgres wger > wger-backup.sql
```

#### Media Files Backup
```bash
# Backup uploaded files
kubectl exec -n wger deployment/wger -- \
  tar -czf /tmp/media-backup.tar.gz /app/media

# Copy locally
kubectl cp wger/wger-xxx:/tmp/media-backup.tar.gz ./wger-media-backup.tar.gz
```

## Troubleshooting

### Application Not Loading

1. **Check pods**:
```bash
kubectl get pods -n wger
kubectl describe pod -n wger -l app.kubernetes.io/name=wger
```

2. **View logs**:
```bash
# Django logs
kubectl logs -n wger -l app.kubernetes.io/component=wger

# Celery logs
kubectl logs -n wger -l app.kubernetes.io/component=celery
```

### Database Connection Issues

1. **Verify credentials**:
```bash
kubectl get secret wger-db-credentials -n wger -o yaml
```

2. **Test connection**:
```bash
kubectl exec -n wger deployment/wger -- \
  python -c "from django.db import connection; connection.ensure_connection()"
```

### Exercise Sync Issues

1. **Check Celery workers**:
```bash
kubectl logs -n wger -l app.kubernetes.io/component=celery-beat
```

2. **Trigger manual sync**:
```bash
kubectl exec -n wger deployment/wger -- \
  python manage.py sync-exercises
```

### Performance Issues

1. **Check Redis**:
```bash
kubectl exec -n wger deployment/redis -- redis-cli ping
```

2. **Monitor resources**:
```bash
kubectl top pods -n wger
```

## Security Considerations

### Authentication
- Django authentication system
- Brute force protection (Axes)
- JWT tokens for API access
- Guest users have limited access

### Data Privacy
- All data stored locally
- No external tracking
- User data isolation
- GDPR compliant

### Best Practices
1. **Strong passwords**: Enforce password policy
2. **Regular updates**: Keep wger updated
3. **Limit registrations**: Consider closing if needed
4. **Monitor access**: Check logs regularly
5. **Backup data**: Regular automated backups

## Customization

### Branding

Modify settings:
```python
# Custom site name
SITE_HEADER = "My Fitness Tracker"
```

### Language Support

Add languages:
```bash
# Generate translations
kubectl exec -n wger deployment/wger -- \
  python manage.py makemessages -l es

# Compile translations
kubectl exec -n wger deployment/wger -- \
  python manage.py compilemessages
```

### Custom Exercises

Via API:
```bash
curl -X POST https://trackit.landryzetam.net/api/v2/exercise/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Exercise",
    "category": 1,
    "description": "Description here"
  }'
```

## API Usage

### Authentication

Get API token:
```bash
curl -X POST https://trackit.landryzetam.net/api/v2/token/ \
  -d "username=user&password=pass"
```

### Example Requests

List workouts:
```bash
curl https://trackit.landryzetam.net/api/v2/workout/ \
  -H "Authorization: Token YOUR_TOKEN"
```

Log weight:
```bash
curl -X POST https://trackit.landryzetam.net/api/v2/weightentry/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -d "weight=75&date=2024-01-01"
```

## Monitoring

### Key Metrics
- Active users count
- Workout completions
- Database size growth
- API request rate
- Cache hit ratio

### Health Checks

Application health:
```bash
curl https://trackit.landryzetam.net/api/v2/status/
```

### Performance Monitoring

Cache statistics:
```bash
kubectl exec -n wger deployment/redis -- redis-cli info stats
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor exercise sync
   - Check error logs
   - Review registrations

2. **Weekly**:
   - Backup database
   - Clean old sessions
   - Update exercises

3. **Monthly**:
   - Review storage usage
   - Update wger version
   - Audit user accounts

### Update Procedure

1. **Update Helm values**:
```yaml
# In release.yaml
spec:
  chart:
    spec:
      version: "0.2.5"  # New version
```

2. **Apply changes**:
```bash
kubectl apply -f apps/base/wger/release.yaml
```

3. **Run migrations**:
```bash
kubectl exec -n wger deployment/wger -- \
  python manage.py migrate
```

### Database Maintenance

Clean old data:
```bash
# Remove old guest accounts
kubectl exec -n wger deployment/wger -- \
  python manage.py cleanup-guests --days=30

# Clean sessions
kubectl exec -n wger deployment/wger -- \
  python manage.py clearsessions
```

## Integration Examples

### With Mobile Apps

Configure for app access:
```yaml
# CORS settings
CORS_ALLOWED_ORIGINS:
  - "capacitor://localhost"
  - "http://localhost"
```

### With Fitness Trackers

Import data via API:
```python
import requests

# Import workout from fitness tracker
data = {
    "date": "2024-01-01",
    "exercises": [...],
    "notes": "Imported from Garmin"
}

response = requests.post(
    "https://trackit.landryzetam.net/api/v2/workout/",
    headers={"Authorization": f"Token {token}"},
    json=data
)
```

### With Monitoring

Prometheus metrics:
```yaml
# Add Django Prometheus
- name: django-prometheus
  image: django-prometheus
  ports:
    - containerPort: 8001
```

## Advanced Features

### Meal Planning

Enable nutrition features:
```yaml
environment:
  - name: WGER_ENABLE_NUTRITION
    value: "True"
```

### Social Features

Enable sharing:
```yaml
environment:
  - name: WGER_ENABLE_SOCIAL
    value: "True"
```

### Custom Workflows

Celery tasks:
```python
# Custom task for reminders
@shared_task
def send_workout_reminder():
    # Send reminders for scheduled workouts
    pass
```

## Future Improvements

- [ ] Add OAuth2 authentication
- [ ] Implement mobile app notifications
- [ ] Create automated workout suggestions
- [ ] Add social features for gym buddies
- [ ] Integrate with wearable devices
- [ ] Add video workout guides
- [ ] Implement AI-powered form checking
- [ ] Create progress prediction models
- [ ] Add meal planning integration
- [ ] Implement coaching features
