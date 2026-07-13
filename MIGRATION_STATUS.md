# Oura Collector: Migration & Backfill Status

**Last Updated:** 2026-07-13 11:20 UTC

## Overall Status: 🔄 IN PROGRESS

### Completed ✅

1. **Database Models Defined**
   - Updated SleepPeriod: +10 new fields
   - Updated Activity: +6 new fields
   - Updated Readiness: +1 new contributor
   - Created SleepPhaseTimeSeries table
   - Created ActivityMetTimeSeries table

2. **Alembic Setup**
   - Initialized Alembic in project
   - Configured env.py for PostgreSQL
   - Created migration file: `001_add_comprehensive_oura_fields.py`
   - Migration includes all schema changes + downgrade support

3. **Docker Build**
   - Fixed Dockerfile to include alembic/ directory and alembic.ini
   - Code pushed to GitHub
   - Docker image build #3 queued → IN PROGRESS

4. **Kubernetes Manifests**
   - Created migration-job.yaml: Runs `alembic upgrade head`
   - Created backfill-job-complete.yaml: 365-day historical backfill
   - Created run-migration-and-backfill.sh: Orchestration script

### In Progress 🔄

1. **Docker Image Build**
   - Current build: #3 (most recent, includes Alembic files)
   - Status: IN PROGRESS
   - Expected time: ~5-10 minutes remaining
   - Awaiting: Image push to DockerHub as `lzetam/oura-collector:latest`

### Pending ⏳

1. **Database Migration (after image ready)**
   ```bash
   kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/migration-job.yaml
   kubectl wait --for=condition=complete job/oura-collector-migrate -n oura-collector --timeout=600s
   ```

2. **Historical Backfill (after migration)**
   ```bash
   kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/backfill-job-complete.yaml
   kubectl wait --for=condition=complete job/oura-collector-backfill -n oura-collector --timeout=1800s
   ```

3. **Data Verification (after backfill)**
   - Query oura_sleep_periods for new fields: period_number, ring_id, etc.
   - Query oura_sleep_phase_timeseries for granular sleep data
   - Query oura_activity_met_timeseries for activity patterns
   - Confirm record counts > 0

## Migration Details

### New Fields Being Added

**oura_sleep_periods** (+10 fields):
- period_number: Which sleep period (1st, 2nd, etc)
- low_battery_alert: Ring battery status during collection
- sleep_score_delta: Change from previous night
- readiness_score_delta: Change from previous night
- sleep_algorithm_version: Algorithm version used
- sleep_analysis_reason: Why analysis was performed
- ring_id: Which ring recorded this sleep
- lowest_heart_rate: Minimum HR during sleep
- average_breath: Breathing rate
- hrv_max, hrv_min, hrv_stdev: HRV statistics

**oura_activity** (+6 fields):
- sedentary_met_minutes: MET minutes while sedentary
- target_meters: Daily activity target in meters
- meters_to_target: How many meters to reach target
- equivalent_walking_distance: Walking equivalent of activity
- class_5_min: Activity intensity per 5-min interval (NEW time-series)
- met: Metabolic equivalent values (NEW time-series)

**oura_readiness** (+1 contributor):
- score_sleep_regularity: Consistency of sleep timing (9th contributor)

### New Time-Series Tables

**oura_sleep_phase_timeseries**
- Granular sleep stage data at 5-min and 30-sec intervals
- Indexes: sleep_period_id, timestamp
- Enables sleep cycle analysis

**oura_activity_met_timeseries**
- Activity classification per 5-min interval
- MET values with sampling interval
- Indexes: activity_date
- Enables activity pattern analysis

## Backfill Strategy

- **Timeframe:** 365 days (1 year of historical data)
- **Smart Backfill:** Only collects data since last sync, no duplicates
- **Expected Duration:** 10-30 minutes depending on API rate limits
- **Output:** Summary statistics showing records collected per data type

## Verification Queries

Once backfill completes, run these queries:

```sql
-- Check sleep periods with new fields
SELECT COUNT(*) as total_periods,
       COUNT(CASE WHEN period_number IS NOT NULL THEN 1 END) as with_period,
       COUNT(CASE WHEN ring_id IS NOT NULL THEN 1 END) as with_ring_id
FROM oura_sleep_periods WHERE date >= NOW() - INTERVAL '90 days';

-- Check sleep phase time-series
SELECT COUNT(*) as phases,
       COUNT(DISTINCT sleep_period_id) as unique_periods,
       MIN(timestamp) as earliest
FROM oura_sleep_phase_timeseries;

-- Check activity with new targets
SELECT COUNT(*) as total_activity,
       COUNT(CASE WHEN target_meters IS NOT NULL THEN 1 END) as with_targets
FROM oura_activity WHERE date >= NOW() - INTERVAL '90 days';

-- Check activity MET time-series
SELECT COUNT(*) as met_records,
       COUNT(DISTINCT activity_date) as unique_days
FROM oura_activity_met_timeseries;
```

## Next Steps

1. **Monitor Build:** Check DockerHub for `lzetam/oura-collector:latest` new push
2. **Run Migration:** Apply migration-job.yaml once image is ready
3. **Run Backfill:** Apply backfill-job-complete.yaml after migration succeeds
4. **Verify Data:** Run SQL queries to confirm data landed
5. **Monitor CronJob:** Set up regular collection every 6 hours

## Troubleshooting

If migration fails:
```bash
kubectl logs job/oura-collector-migrate -n oura-collector
kubectl describe job/oura-collector-migrate -n oura-collector
```

If backfill fails:
```bash
kubectl logs job/oura-collector-backfill -n oura-collector -f
kubectl events -n oura-collector | grep backfill
```

To manually connect to database:
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app
```

## Timeline

- 11:06 - Code pushed with Alembic setup
- 11:09 - Dockerfile fix pushed (include alembic files)
- 11:10 - Build started
- 11:20 - Build in progress, documentation prepared
- TBD - Build complete, migration job triggered
- TBD - Migration complete, backfill job triggered
- TBD - Backfill complete, data verified
