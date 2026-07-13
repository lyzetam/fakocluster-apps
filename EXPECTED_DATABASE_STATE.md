# Expected Database State After Backfill

This document shows what the database will look like when the automation completes successfully.

## Table Row Counts

**After 365-day backfill from Oura API:**

```
oura_sleep_periods              ~365 rows (one per night for a year)
oura_daily_sleep                ~365 rows
oura_activity                   ~365 rows (one per day)
oura_readiness                  ~365 rows
oura_workouts                   ~50-100 rows (varies by activity)
oura_stress                      ~365 rows
oura_heart_rate                  ~365 rows
oura_session                     ~50-200 rows
oura_vo2_max                     ~12 rows (monthly)
oura_cardiovascular_age          ~12 rows (monthly)
oura_resilience                  ~365 rows
oura_spo2                        ~365 rows
oura_tag                         ~100-500 rows
oura_sleep_time                  ~365 rows
oura_rest_mode_period            ~100-500 rows
oura_ring_configuration          ~5-10 rows (config changes)

=== NEW TABLES ===
oura_sleep_phase_timeseries      ~5000-10000 rows (multiple per night)
oura_activity_met_timeseries     ~365 rows (one per day with time-series)
```

**Total new rows added: 5500-11000 across the two new tables**

---

## Sample Records After Backfill

### oura_sleep_periods (with 28 fields)

```
id          | 12345
period_id   | 'sleep-abc123-20260701'
date        | 2026-07-01
type        | 'main'
period_number | 1  ← NEW
score       | 78
bedtime_start | 2026-06-30 22:30:00
bedtime_end | 2026-07-01 06:45:00
total_sleep_hours | 8.25
time_in_bed_hours | 8.5
rem_hours   | 1.83
deep_hours  | 1.42
light_hours | 4.75
awake_time  | 0.25
rem_percentage | 22.0
deep_percentage | 17.2
light_percentage | 57.6
efficiency_percent | 97.0
latency_minutes | 8.0
restless_periods | 2
heart_rate_avg | 54.2
heart_rate_min | 48.0
lowest_heart_rate | 47.0  ← NEW
hrv_avg     | 45.3
hrv_max     | 68.0
hrv_min     | 24.0
hrv_stdev   | 12.5
respiratory_rate | 14.5
average_breath | 14.5  ← NEW
has_heart_rate_data | true
has_hrv_data | true
low_battery_alert | false  ← NEW
sleep_score_delta | 3  ← NEW
readiness_score_delta | -2  ← NEW
sleep_algorithm_version | 'v4.1'  ← NEW
sleep_analysis_reason | 'foreground_sleep_analysis'  ← NEW
ring_id     | 'ring-abc123def456'  ← NEW
created_at  | 2026-07-13 11:35:00
raw_data    | JSON object
```

### oura_sleep_phase_timeseries (NEW TABLE)

```
id          | 1
sleep_period_id | 'sleep-abc123-20260701'
timestamp   | 2026-06-30 22:30:00
sleep_phase_5_min | '1,1,2,2,3,3,3,2,2,1,1,2,2,2,3,...'
sleep_phase_30_sec | '1,1,1,1,2,2,2,2,2,3,3,3,3,3,2,...'
movement_30_sec | '0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,...'
created_at  | 2026-07-13 11:35:00

id          | 2
sleep_period_id | 'sleep-abc123-20260701'
timestamp   | 2026-06-30 22:35:00
sleep_phase_5_min | '2,2,3,3,3,3,2,2,1,1,1,2,2,3,3,...'
sleep_phase_30_sec | '2,2,2,2,3,3,3,3,3,2,2,1,1,1,1,...'
movement_30_sec | '0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,...'
created_at  | 2026-07-13 11:35:00

... (300+ more records for this sleep period)
```

### oura_activity (with 24 fields)

```
id          | 5678
date        | 2026-07-01
activity_score | 82
steps       | 12450
distance_meters | 9240
distance_km | 9.24
equivalent_walking_distance | 9.8  ← NEW
calories_active | 520
calories_total | 2380
calories_target | 2000
high_activity_minutes | 45.0
medium_activity_minutes | 120.0
low_activity_minutes | 240.0
sedentary_minutes | 840.0
sedentary_met_minutes | 1050.0  ← NEW
non_wear_minutes | 15.0
resting_time_minutes | 120.0
total_active_minutes | 405.0
met_minutes | 1850.0
average_met_minutes | 3.2
high_activity_met_minutes | 420.0
medium_activity_met_minutes | 680.0
low_activity_met_minutes | 450.0
target_meters | 10000  ← NEW
meters_to_target | 760  ← NEW
inactivity_alerts | 0
score_meet_daily_targets | 85
score_move_every_hour | 88
score_recovery_time | 82
score_stay_active | 78
score_training_frequency | 75
score_training_volume | 80
created_at  | 2026-07-13 11:35:00
raw_data    | JSON object
```

### oura_activity_met_timeseries (NEW TABLE)

```
id          | 9999
activity_date | 2026-07-01
class_5_min | 'rest,rest,low,low,medium,high,high,medium,low,low,...'
met_interval | 300  (seconds)
met_items   | [1.2, 1.3, 1.4, 2.1, 3.5, 6.2, 7.1, 5.8, 2.1, ...]
met_timestamp | 2026-07-01 00:00:00
created_at  | 2026-07-13 11:35:00
```

### oura_readiness (with 11 fields including 9 contributors)

```
id          | 6789
date        | 2026-07-01
readiness_score | 74
temperature_deviation | 0.15
temperature_trend_deviation | 0.08
recovery_index | 65.0
resting_heart_rate | 54.2
hrv_balance | 48.5
score_activity_balance | 82
score_body_temperature | 78
score_hrv_balance | 71
score_previous_day_activity | 75
score_previous_night | 78
score_recovery_index | 68
score_resting_heart_rate | 81
score_sleep_balance | 72
score_sleep_regularity | 76  ← NEW (9th contributor)
timestamp   | 2026-07-01 10:00:00
created_at  | 2026-07-13 11:35:00
raw_data    | JSON object
```

---

## Verification Queries & Results

### Query 1: Sleep Periods Count
```sql
SELECT COUNT(*) FROM oura_sleep_periods;
```
**Expected Result:** `365` (approximately, ±7 for weekends/missed days)

### Query 2: Sleep Phase Time-Series Granularity
```sql
SELECT 
  COUNT(*) as total_phases,
  COUNT(DISTINCT sleep_period_id) as unique_periods,
  COUNT(DISTINCT DATE(timestamp)) as unique_dates
FROM oura_sleep_phase_timeseries;
```
**Expected Result:**
```
total_phases    | 5000-10000
unique_periods  | ~365
unique_dates    | ~365
```

### Query 3: New Fields Populated
```sql
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN period_number IS NOT NULL THEN 1 END) as with_period,
  COUNT(CASE WHEN ring_id IS NOT NULL THEN 1 END) as with_ring_id,
  COUNT(CASE WHEN low_battery_alert IS NOT NULL THEN 1 END) as with_battery
FROM oura_sleep_periods;
```
**Expected Result:**
```
total        | ~365
with_period  | ~365
with_ring_id | ~365
with_battery | ~365
```

### Query 4: Activity Targets
```sql
SELECT 
  COUNT(*) as total,
  AVG(target_meters) as avg_target,
  AVG(meters_to_target) as avg_to_target,
  AVG(equivalent_walking_distance) as avg_equiv_walk
FROM oura_activity;
```
**Expected Result:**
```
total             | ~365
avg_target        | ~10000
avg_to_target     | varies (-500 to +500)
avg_equiv_walk    | ~9-10 km
```

### Query 5: Activity MET Time-Series
```sql
SELECT 
  COUNT(*) as total,
  COUNT(DISTINCT activity_date) as unique_dates,
  COUNT(CASE WHEN met_items IS NOT NULL THEN 1 END) as with_met_data
FROM oura_activity_met_timeseries;
```
**Expected Result:**
```
total        | ~365
unique_dates | ~365
with_met_data | ~365
```

### Query 6: Sleep Regularity Contributor
```sql
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN score_sleep_regularity IS NOT NULL THEN 1 END) as with_regularity,
  AVG(score_sleep_regularity) as avg_regularity_score
FROM oura_readiness;
```
**Expected Result:**
```
total            | ~365
with_regularity  | ~365
avg_regularity   | 70-80 (depending on user's sleep consistency)
```

---

## Data Quality Checks

### Sleep Data Sanity
- Sleep hours: 4-12 hours per night
- Deep sleep: 10-25% of total
- REM sleep: 15-25% of total
- Efficiency: 80-99%

### Activity Data Sanity
- Steps: 0-30,000 per day
- Activity score: 0-100
- MET minutes: 500-3000 per day

### Readiness Data Sanity
- Readiness score: 0-100
- Heart rate: 40-80 bpm (resting)
- Temperature deviation: ±0.5°C

---

## Failure Indicators

❌ **If ANY of these are true, backfill did NOT complete:**
- Total rows in new tables = 0
- New columns have NULL in >50% of rows
- Date ranges do NOT span ~365 days
- Any queries timeout or error
- Job status ≠ "1/1"

✅ **If ALL of these are true, backfill SUCCEEDED:**
- oura_sleep_phase_timeseries > 1000 rows
- oura_activity_met_timeseries ~365 rows
- All new fields populated in 95%+ of rows
- Date ranges span last 365 days
- All queries return in <1 second
- Job status = "1/1"

---

## Next Steps After Verification

Once data is confirmed:

1. **Monitor Regular Collection**
   ```bash
   kubectl logs -f deployment/oura-collector -n oura-collector
   ```

2. **Check CronJob Schedule**
   ```bash
   kubectl get cronjob -n oura-collector
   # Should run every 6 hours
   ```

3. **Build Reports/Dashboards**
   - Use oura_sleep_phase_timeseries for sleep cycle analysis
   - Use oura_activity_met_timeseries for workout tracking
   - Use new fields (ring_id, battery_alert) for device diagnostics

4. **Archive This Setup**
   - Document what was collected
   - Set baseline metrics
   - Configure alerts for anomalies

---

## Timeline to Completion

| Step | Duration | Total Time |
|------|----------|------------|
| Docker build | 15 min | 15 min |
| Alembic migration | 5 min | 20 min |
| Backfill (365 days) | 20 min | 40 min |
| Verification | 1 min | 41 min |

**Total: ~40 minutes from now**

---

## Status: READY FOR DATA VERIFICATION

Once the `full-backfill-automation.sh` script completes, you will see output like:

```
[✅] COMPLETE DATA COLLECTION WORKFLOW FINISHED

Summary:
- New tables created: oura_sleep_phase_timeseries, oura_activity_met_timeseries
- New fields added: 17 columns across 3 tables
- Records in sleep_periods: 365+
- Records in sleep_phase_timeseries: 5000+
- Records in activity: 365+
- Records in activity_met_timeseries: 365+

Data is now LIVE in the database! ✨
```

**At that point, the mission is complete!**
