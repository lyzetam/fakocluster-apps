# Oura Collector - Health Data Collection Service

## Overview

Oura Collector is an automated health data collection service deployed in the Fako cluster. It integrates with the Oura Ring API to collect personal health metrics including sleep, activity, readiness, and heart rate data. The service stores this data in PostgreSQL for analysis and visualization. It features scheduled collection, backfill capabilities, and secure credential management through AWS Secrets Manager. This enables long-term health tracking and analysis within your personal infrastructure.

## Key Features

- **Automated Collection**: Hourly data synchronization from Oura API
- **Data Backfill**: Historical data collection up to 30 days
- **PostgreSQL Storage**: Structured storage for analytics
- **AWS Secrets Integration**: Secure API credential management
- **Prometheus Metrics**: Service health monitoring
- **Health Checks**: Liveness and readiness probes
- **Persistent Storage**: Local data caching
- **Error Handling**: Retry logic with exponential backoff

## Architecture

### Components

1. **Deployment**: Single-replica stateful service
2. **CronJob**: Optional scheduled collection
3. **Service**: ClusterIP on port 8080
4. **Storage**: PostgreSQL database and local PVC
5. **External Secrets**: AWS Secrets Manager integration
6. **ServiceMonitor**: Prometheus metrics export

### Resource Requirements

- **Memory**: 256Mi (request), 512Mi (limit)
- **CPU**: 100m (request), 500m (limit)
- **Storage**: Persistent volume for local cache
- **Database**: PostgreSQL connection

## Configuration

### Environment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `STORAGE_BACKEND` | `postgres` | Database backend |
| `DATABASE_NAME` | `app` | PostgreSQL database |
| `COLLECTION_INTERVAL` | `3600` | 1 hour between collections |
| `DAYS_TO_BACKFILL` | `30` | Historical data range |
| `API_TIMEOUT` | `30` | API request timeout |
| `MAX_RETRIES` | `3` | Retry attempts |

### AWS Secrets

Required secrets in AWS Secrets Manager:
- `oura/api-credentials`: Oura API token
- `postgres/app-user`: Database credentials

## Usage

### Initial Setup

1. **Configure Oura API Token**:
```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name oura/api-credentials \
  --secret-string '{"OURA_API_TOKEN":"your-token-here"}'
```

2. **Verify deployment**:
```bash
kubectl get deployment -n oura-collector oura-collector
kubectl logs -n oura-collector -l app=oura-collector
```

### Data Collection

The collector automatically:
1. Fetches data every hour
2. Backfills up to 30 days on first run
3. Stores data in PostgreSQL
4. Updates collection timestamp

### Accessing Data

Query collected data:
```sql
-- Connect to PostgreSQL
kubectl exec -it -n postgres postgres-cluster-1 -- psql -U app

-- View sleep data
SELECT date, total_sleep, rem_sleep, deep_sleep 
FROM oura_sleep 
ORDER BY date DESC 
LIMIT 7;

-- View activity data
SELECT date, steps, active_calories, total_calories 
FROM oura_activity 
ORDER BY date DESC 
LIMIT 7;
```

## Data Types Collected

### Sleep Metrics
- Total sleep duration
- REM sleep
- Deep sleep
- Light sleep
- Sleep efficiency
- Bedtime/wake time

### Activity Metrics
- Steps
- Active calories
- Total calories
- Activity score
- Movement data

### Readiness Metrics
- Readiness score
- HRV (Heart Rate Variability)
- Resting heart rate
- Body temperature deviation

### Heart Rate Data
- Continuous heart rate
- Heart rate zones
- Recovery metrics

## Operations

### Manual Data Collection

Trigger immediate collection:
```bash
# Force collection
kubectl exec -n oura-collector deployment/oura-collector -- \
  python /app/collect.py --force
```

### Backfill Historical Data

Collect specific date range:
```bash
# Backfill specific period
kubectl exec -n oura-collector deployment/oura-collector -- \
  python /app/collect.py --start-date 2024-01-01 --end-date 2024-12-31
```

### Health Monitoring

```bash
# Check health endpoint
kubectl port-forward -n oura-collector svc/oura-collector 8080:8080
curl http://localhost:8080/health

# View metrics
curl http://localhost:8080/metrics
```

## Troubleshooting

### Collection Failures

1. **Check logs**:
```bash
kubectl logs -n oura-collector -l app=oura-collector --tail=100
```

2. **Verify API token**:
```bash
# Check if secret exists
kubectl get secret aws-credentials-env -n oura-collector

# Test API access
kubectl exec -n oura-collector deployment/oura-collector -- \
  curl -H "Authorization: Bearer $OURA_API_TOKEN" \
  https://api.ouraring.com/v2/usercollection/personal_info
```

### Database Connection Issues

1. **Verify credentials**:
```bash
kubectl describe externalsecret -n oura-collector
```

2. **Test connection**:
```bash
kubectl exec -n oura-collector deployment/oura-collector -- \
  pg_isready -h postgres-cluster-rw.postgres.svc.cluster.local -p 5432
```

### Rate Limiting

Oura API limits:
- 5000 requests per hour
- Collector implements backoff strategy
- Check `X-RateLimit-Remaining` in logs

## Security Considerations

### API Token Security
- Token stored in AWS Secrets Manager
- Never logged or exposed
- Rotation supported

### Database Security
- Credentials from AWS Secrets
- SSL connection to PostgreSQL
- Limited database permissions

### Best Practices
1. **Rotate tokens**: Regular API token rotation
2. **Monitor access**: Audit API usage
3. **Backup data**: Regular database backups
4. **Privacy**: Ensure data handling compliance
5. **Access control**: Limit namespace access

## Data Analysis

### Example Queries

Sleep quality trends:
```sql
-- Weekly sleep averages
SELECT 
  DATE_TRUNC('week', date) as week,
  AVG(total_sleep) as avg_sleep,
  AVG(sleep_efficiency) as avg_efficiency
FROM oura_sleep
GROUP BY week
ORDER BY week DESC;
```

Activity patterns:
```sql
-- Daily activity vs readiness
SELECT 
  a.date,
  a.steps,
  a.activity_score,
  r.readiness_score
FROM oura_activity a
JOIN oura_readiness r ON a.date = r.date
ORDER BY a.date DESC;
```

### Integration with Grafana

Create dashboards:
```yaml
# Datasource configuration
apiVersion: 1
datasources:
  - name: Oura-PostgreSQL
    type: postgres
    url: postgres-cluster-rw.postgres:5432
    database: app
```

## Monitoring

### Key Metrics

- `oura_collector_collections_total`: Total collections
- `oura_collector_errors_total`: Collection errors
- `oura_collector_last_collection_timestamp`: Last success
- `oura_collector_api_requests_total`: API call count
- `oura_collector_rate_limit_remaining`: API quota

### Alerts

Configure alerts:
```yaml
# PrometheusRule
- alert: OuraCollectionFailed
  expr: time() - oura_collector_last_collection_timestamp > 7200
  annotations:
    summary: "Oura collection hasn't run in 2 hours"
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Check collection status
   - Monitor error logs
   - Verify data integrity

2. **Weekly**:
   - Review API usage
   - Check storage usage
   - Analyze collection patterns

3. **Monthly**:
   - Rotate API tokens
   - Clean old logs
   - Update collector image

### Database Maintenance

```bash
# Vacuum tables
kubectl exec -n postgres postgres-cluster-1 -- \
  psql -U app -c "VACUUM ANALYZE oura_sleep, oura_activity;"

# Check table sizes
kubectl exec -n postgres postgres-cluster-1 -- \
  psql -U app -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) 
  FROM pg_stat_user_tables WHERE schemaname='public';"
```

### Backup Strategy

```bash
# Backup Oura data
kubectl exec -n postgres postgres-cluster-1 -- \
  pg_dump -U app -t 'oura_*' app > oura-backup-$(date +%Y%m%d).sql
```

## Advanced Configuration

### Custom Collection Schedule

Modify CronJob:
```yaml
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
```

### Additional Metrics

Enable detailed metrics:
```yaml
data:
  ENABLE_DETAILED_METRICS: "true"
  COLLECT_WORKOUTS: "true"
  COLLECT_TAGS: "true"
```

### Multi-User Support

Configure for multiple Oura accounts:
```yaml
data:
  MULTI_USER_MODE: "true"
  USER_MAPPING: |
    user1:token1
    user2:token2
```

## Integration Examples

### With n8n Workflows

Trigger analysis on new data:
```json
{
  "nodes": [{
    "name": "Oura Data Trigger",
    "type": "n8n-nodes-base.webhook",
    "webhookPath": "oura-new-data"
  }]
}
```

### With Jupyter Notebooks

Analysis environment:
```python
import pandas as pd
import psycopg2

# Connect to database
conn = psycopg2.connect(
    host="postgres-cluster-rw.postgres",
    database="app",
    user="app"
)

# Load sleep data
sleep_df = pd.read_sql(
    "SELECT * FROM oura_sleep ORDER BY date", 
    conn
)
```

## Future Improvements

- [ ] Add real-time data streaming
- [ ] Implement data export features
- [ ] Create mobile app integration
- [ ] Add anomaly detection
- [ ] Implement data visualization UI
- [ ] Add integration with other health devices
- [ ] Create health insights engine
- [ ] Add data anonymization features
- [ ] Implement FHIR compliance
- [ ] Create API for third-party access
