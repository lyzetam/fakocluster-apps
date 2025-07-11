# Oura Dashboard Data Troubleshooting Guide

## Issue: Dashboard showing data from 1 week ago

### Potential Causes and Solutions

#### 1. **Collector Default Configuration (Most Likely)**
The oura-collector is configured with `DAYS_TO_BACKFILL=7` by default, which means:
- On each run, it only fetches the last 7 days of data
- If the collector hasn't run recently, you'll only see data up to 7 days ago

**Solutions:**
- Check if the collector is running: `kubectl get pods -n oura-collector`
- Check collector logs: `kubectl logs -n oura-collector <pod-name>`
- Increase DAYS_TO_BACKFILL environment variable or in AWS Secrets Manager

#### 2. **Collector Not Running**
The collector might have stopped or crashed.

**Check:**
```bash
# Check if collector pod is running
kubectl get pods -n oura-collector

# Check pod events
kubectl describe pod -n oura-collector <pod-name>

# Check logs for errors
kubectl logs -n oura-collector <pod-name> --tail=100
```

#### 3. **Database Connection Issues**
The collector might be unable to write to the database.

**Check:**
- Database connectivity from collector
- Database credentials in AWS Secrets Manager
- Database disk space and performance

#### 4. **Oura API Issues**
- API token might have expired
- Rate limiting from Oura API
- Oura service outage

**Check collector logs for:**
- "Failed to connect to Oura API"
- HTTP 401 (unauthorized) errors
- HTTP 429 (rate limit) errors

#### 5. **Collection Schedule**
If using continuous mode, check:
- `COLLECTION_INTERVAL` setting (default: 3600 seconds = 1 hour)
- `RUN_ONCE` setting (if true, collector exits after one run)

### Immediate Actions

1. **Run a manual collection with more days:**
   ```bash
   # Set environment variable to collect 30 days
   kubectl set env deployment/oura-collector -n oura-collector DAYS_TO_BACKFILL=30
   
   # Restart the collector
   kubectl rollout restart deployment/oura-collector -n oura-collector
   ```

2. **Check collection logs:**
   ```bash
   kubectl logs -n oura-collector -l app=oura-collector --tail=200 -f
   ```

3. **Verify data in database:**
   ```sql
   -- Connect to PostgreSQL and check latest data
   SELECT MAX(date) as latest_date, COUNT(*) as record_count 
   FROM activity
   UNION ALL
   SELECT MAX(date), COUNT(*) FROM readiness
   UNION ALL
   SELECT MAX(date), COUNT(*) FROM daily_sleep;
   ```

### Long-term Solutions

1. **Update AWS Secrets Manager** with appropriate settings:
   ```json
   {
     "oura_personal_access_token": "YOUR_TOKEN",
     "collection_interval": 3600,
     "days_to_backfill": 30,
     "collect_all_endpoints": true
   }
   ```

2. **Set up monitoring:**
   - Alert when collector hasn't run in 24 hours
   - Alert when latest data is older than 2 days
   - Monitor collector pod restarts

3. **Configure collector for reliability:**
   - Use CronJob instead of continuous deployment for predictable runs
   - Add retry logic for transient failures
   - Implement proper health checks

### Collector Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| DAYS_TO_BACKFILL | 7 | Number of days to fetch on each run |
| COLLECTION_INTERVAL | 3600 | Seconds between collections (continuous mode) |
| RUN_ONCE | false | Exit after one collection |
| LOG_LEVEL | INFO | Logging verbosity |

### Quick Diagnostic Script

```bash
#!/bin/bash
echo "=== Oura Data Collection Diagnostics ==="

echo -e "\n1. Checking collector pod status:"
kubectl get pods -n oura-collector

echo -e "\n2. Recent collector logs:"
kubectl logs -n oura-collector -l app=oura-collector --tail=20

echo -e "\n3. Checking environment variables:"
kubectl get deployment oura-collector -n oura-collector -o jsonpath='{.spec.template.spec.containers[0].env[*]}' | jq

echo -e "\n4. Last collection time from logs:"
kubectl logs -n oura-collector -l app=oura-collector | grep "Collection summary:" | tail -1

echo -e "\n5. Database connection test:"
kubectl exec -n oura-collector deployment/oura-collector -- python -c "
from collector import OuraCollector
c = OuraCollector()
print('Database connection: OK')
"
