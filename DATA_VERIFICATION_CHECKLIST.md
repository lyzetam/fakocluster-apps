# Oura Collector: Data Verification Checklist

## Expected Results After Backfill Completes

### ✅ Phase 1: Migration Complete
- [ ] `alembic_version` table exists with revision '001'
- [ ] No migration errors in job logs
- [ ] `oura_sleep_periods` table has 10 new columns
- [ ] `oura_activity` table has 6 new columns  
- [ ] `oura_readiness` table has 1 new column
- [ ] `oura_sleep_phase_timeseries` table exists with 3 columns
- [ ] `oura_activity_met_timeseries` table exists with 4 columns

### ✅ Phase 2: Backfill Complete
- [ ] No backfill job errors
- [ ] Collector collected data for 365 days
- [ ] No rate-limiting or API errors in logs

### ✅ Phase 3: Data in Database

#### Sleep Periods Table
```sql
SELECT COUNT(*) FROM oura_sleep_periods;
-- Expected: > 0 rows (should have 365+ days of sleep data)

SELECT COUNT(DISTINCT DATE(date)) FROM oura_sleep_periods;
-- Expected: Should be close to 365 (one entry per day)

SELECT COUNT(*) FROM oura_sleep_periods 
WHERE period_number IS NOT NULL;
-- Expected: Most rows should have period_number (which sleep of the day)

SELECT COUNT(*) FROM oura_sleep_periods 
WHERE ring_id IS NOT NULL;
-- Expected: Most rows should have ring_id

SELECT sample_row FROM oura_sleep_periods LIMIT 1;
-- Expected output should show all 28 fields populated
```

**Verification Command:**
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app -c "\
SELECT 
  date, sleep_score, total_sleep_hours,
  period_number, ring_id, low_battery_alert,
  sleep_algorithm_version, sleep_score_delta
FROM oura_sleep_periods 
LIMIT 5 \gx"
```

#### Sleep Phase Time-Series Table  
```sql
SELECT COUNT(*) FROM oura_sleep_phase_timeseries;
-- Expected: > 10000 rows (many 5-min and 30-sec intervals per night)

SELECT COUNT(DISTINCT sleep_period_id) FROM oura_sleep_phase_timeseries;
-- Expected: Should match or be close to oura_sleep_periods count

SELECT COUNT(DISTINCT DATE(timestamp)) FROM oura_sleep_phase_timeseries;
-- Expected: Should be close to 365 (multiple entries per day)

SELECT * FROM oura_sleep_phase_timeseries LIMIT 1;
-- Expected: sleep_phase_5_min and sleep_phase_30_sec columns populated
```

**Verification Command:**
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app -c "\
SELECT 
  sleep_period_id, timestamp,
  sleep_phase_5_min, sleep_phase_30_sec, movement_30_sec
FROM oura_sleep_phase_timeseries 
LIMIT 5 \gx"
```

#### Activity Table
```sql
SELECT COUNT(*) FROM oura_activity;
-- Expected: ~ 365 rows (one per day)

SELECT COUNT(*) FROM oura_activity 
WHERE target_meters IS NOT NULL;
-- Expected: All rows should have target_meters

SELECT COUNT(*) FROM oura_activity 
WHERE sedentary_met_minutes IS NOT NULL;
-- Expected: All rows should have sedentary_met_minutes

SELECT AVG(equivalent_walking_distance), 
       AVG(meters_to_target) 
FROM oura_activity;
-- Expected: Should show meaningful averages (not NULL)
```

**Verification Command:**
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app -c "\
SELECT 
  date, activity_score, steps,
  target_meters, meters_to_target,
  equivalent_walking_distance,
  sedentary_met_minutes
FROM oura_activity 
ORDER BY date DESC LIMIT 5 \gx"
```

#### Activity MET Time-Series Table
```sql
SELECT COUNT(*) FROM oura_activity_met_timeseries;
-- Expected: ~ 365 rows (one per day with MET data)

SELECT COUNT(DISTINCT activity_date) FROM oura_activity_met_timeseries;
-- Expected: Should match oura_activity count

SELECT COUNT(*) FROM oura_activity_met_timeseries 
WHERE met_items IS NOT NULL;
-- Expected: All rows should have MET time-series data
```

**Verification Command:**
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app -c "\
SELECT 
  activity_date, class_5_min, met_interval,
  json_array_length(met_items) as met_count
FROM oura_activity_met_timeseries 
ORDER BY activity_date DESC LIMIT 5 \gx"
```

#### Readiness Table
```sql
SELECT COUNT(*) FROM oura_readiness;
-- Expected: ~ 365 rows

SELECT COUNT(*) FROM oura_readiness 
WHERE score_sleep_regularity IS NOT NULL;
-- Expected: All rows should have the new sleep_regularity contributor
```

**Verification Command:**
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- psql -U postgres -d app -c "\
SELECT 
  date, readiness_score,
  score_sleep_regularity,
  score_body_temperature, score_hrv_balance
FROM oura_readiness 
ORDER BY date DESC LIMIT 5 \gx"
```

### ✅ Phase 4: Data Quality

#### Completeness Check
- [ ] New fields populated (not NULL) in most rows
- [ ] Date ranges span 365 days
- [ ] No duplicate records in time-series

#### Sanity Check
- [ ] Sleep hours: 0-12 hours
- [ ] Activity scores: 0-100
- [ ] Readiness scores: 0-100  
- [ ] Heart rates: 40-120 bpm
- [ ] HRV values: 10-100 ms

## Troubleshooting

### If no data appears in database:

1. Check migration ran successfully:
```bash
kubectl logs job/oura-collector-migrate -n oura-collector | tail -30
```

2. Check backfill ran successfully:
```bash
kubectl logs job/oura-collector-backfill -n oura-collector | tail -50
```

3. Check Oura API connectivity:
```bash
kubectl logs job/oura-collector-backfill -n oura-collector | grep -i "api\|error\|connection"
```

4. Manually query database:
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- \
  psql -U postgres -d app -c "SELECT COUNT(*) FROM oura_sleep_periods;"
```

### If migration failed:

1. Check error:
```bash
kubectl logs job/oura-collector-migrate -n oura-collector
```

2. Verify schema was created:
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- \
  psql -U postgres -d app -c "\d oura_sleep_phase_timeseries"
```

3. Check Alembic version:
```bash
kubectl exec -it postgres-cluster-rw-0 -n postgres -- \
  psql -U postgres -d app -c "SELECT * FROM alembic_version;"
```

### If backfill timed out:

1. Check if job is still running:
```bash
kubectl get job/oura-collector-backfill -n oura-collector -o wide
```

2. View real-time logs:
```bash
kubectl logs job/oura-collector-backfill -n oura-collector -f
```

3. Check pod events:
```bash
kubectl describe pod -n oura-collector -l job-name=oura-collector-backfill
```

## Success Criteria

✅ **DATA IS CONFIRMED IN DATABASE WHEN:**
1. Migration job completes (status: 1/1)
2. Backfill job completes (status: 1/1)
3. sleep_periods count > 0
4. sleep_phase_timeseries count > 1000
5. activity count > 0
6. activity_met_timeseries count > 0
7. New columns (period_number, ring_id, etc) are populated
8. All data types have reasonable values

## Timeline Expectations

| Step | Duration | Notes |
|------|----------|-------|
| Docker Build | 15-20 min | Waiting on GH Actions |
| Alembic Migration | 2-5 min | Create tables/columns |
| Historical Backfill | 10-30 min | 365 days, API rate-limited |
| Database Verification | 1 min | Query verification |
| **TOTAL** | **25-60 min** | Depends on Oura API responsiveness |

## Success Summary

Once all checks pass:
- ✅ Database schema updated with all 44 new fields
- ✅ 2 new time-series tables created and populated
- ✅ 365 days of historical health data collected
- ✅ New collector deployment ready for daily collection
- ✅ Health monitoring system fully operational

**Status: READY FOR PRODUCTION** 🚀
