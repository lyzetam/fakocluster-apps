# Oura Data Collector

Enhanced Oura Ring data collector with PostgreSQL support and smart backfill capabilities.

## Features

- **Smart Backfill**: Automatically detects the last collected data and only fetches new data since then
- **Comprehensive Data Collection**: Collects all available Oura API endpoints
- **PostgreSQL Storage**: Stores data in a structured PostgreSQL database
- **Health Check Endpoint**: Provides health status at port 8080
- **Configurable Collection**: Supports both one-time and continuous collection modes

## Smart Backfill Logic

The collector now implements intelligent data collection to prevent gaps and minimize redundant API calls:

1. **Initial Collection**: When no data exists, it collects data for the configured `DAYS_TO_BACKFILL` period
2. **Subsequent Collections**: Automatically detects the most recent data in the database and only fetches new data since then
3. **Gap Prevention**: Even if the collector is down for extended periods, it will fill in missing data up to the configured backfill limit
4. **Manual Override**: You can still force a specific date range collection when needed

## Configuration

The collector is configured via environment variables and AWS Secrets Manager.

### Environment Variables (ConfigMap)

```yaml
COLLECTION_INTERVAL: "3600"  # Collection interval in seconds (1 hour)
DAYS_TO_BACKFILL: "30"      # Maximum days to backfill
RUN_ONCE: "false"           # Set to "true" for one-time collection
LOG_LEVEL: "INFO"           # Logging level
API_TIMEOUT: "30"           # API request timeout in seconds
MAX_RETRIES: "3"            # Maximum API retry attempts
RETRY_DELAY: "5"            # Delay between retries in seconds
```

### AWS Secrets Manager

#### Oura Credentials (`oura/api-credentials`)
```json
{
  "oura_personal_access_token": "YOUR_TOKEN",
  "collection_interval": 3600,
  "days_to_backfill": 30,
  "collect_all_endpoints": true
}
```

#### PostgreSQL Credentials (`postgres/app-user`)
```json
{
  "username": "your_username",
  "password": "your_password",
  "host": "your-database-host.region.rds.amazonaws.com",
  "port": 5432,
  "database": "oura_health"
}
```

## Deployment

The collector is designed to run in Kubernetes:

```bash
# Deploy with updated image
kubectl set image deployment/oura-collector oura-collector=your-registry/oura-collector:latest -n oura-collector

# Update configuration
kubectl edit configmap oura-collector-config -n oura-collector

# Restart to apply changes
kubectl rollout restart deployment/oura-collector -n oura-collector
```

## Monitoring

Check collector status:
```bash
# View logs
kubectl logs -n oura-collector -l app=oura-collector -f

# Check health
kubectl exec -n oura-collector deployment/oura-collector -- curl localhost:8080/health

# View collection summary from logs
kubectl logs -n oura-collector -l app=oura-collector | grep "Collection summary:"
```

## Troubleshooting

### Data Not Updating

1. Check if the collector is running:
   ```bash
   kubectl get pods -n oura-collector
   ```

2. Check for errors in logs:
   ```bash
   kubectl logs -n oura-collector -l app=oura-collector --tail=100
   ```

3. Verify database connectivity:
   ```bash
   kubectl exec -n oura-collector deployment/oura-collector -- python -c "from collector import OuraCollector; c = OuraCollector(); print('DB OK')"
   ```

### Manual Data Backfill

To manually collect a specific number of days:
```bash
# Set RUN_ONCE=true and DAYS_TO_BACKFILL to desired value
kubectl set env deployment/oura-collector -n oura-collector RUN_ONCE=true DAYS_TO_BACKFILL=60
kubectl rollout restart deployment/oura-collector -n oura-collector

# After collection completes, restore continuous mode
kubectl set env deployment/oura-collector -n oura-collector RUN_ONCE=false DAYS_TO_BACKFILL=30
kubectl rollout restart deployment/oura-collector -n oura-collector
```

## Data Collected

The collector fetches and processes the following data types:

- **Personal Info**: User profile information
- **Sleep Periods**: Detailed sleep stages and metrics
- **Daily Sleep**: Sleep scores and contributors
- **Activity**: Daily activity metrics and scores
- **Readiness**: Recovery and readiness scores
- **Workouts**: Exercise sessions
- **Stress**: Daily stress levels (if available)
- **Heart Rate**: Time-series heart rate data
- **SpO2**: Blood oxygen levels
- **Sessions**: Meditation/breathing sessions
- **Tags**: User-created tags and notes

## Version History

- **v2.0**: Added smart backfill to prevent data gaps
- **v1.0**: Initial release with basic collection capabilities
