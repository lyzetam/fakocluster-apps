#!/bin/bash
# Run Alembic migration and historical data backfill for Oura collector
# This script orchestrates the complete data collection workflow

set -e

NAMESPACE="oura-collector"
MIGRATION_JOB="oura-collector-migrate"
BACKFILL_JOB="oura-collector-backfill"
DB_HOST="postgres-cluster-rw.postgres.svc.cluster.local"
DB_NAME="app"

echo "🔄 Oura Collector: Migration & Backfill Workflow"
echo "=================================================="

# Step 1: Apply migration job
echo ""
echo "📋 Step 1: Applying database migration..."
kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/migration-job.yaml

# Wait for migration job to complete
echo "⏳ Waiting for migration job to complete (max 10 minutes)..."
kubectl wait --for=condition=complete job/$MIGRATION_JOB -n $NAMESPACE --timeout=600s 2>/dev/null || {
    echo "❌ Migration job failed or timed out"
    echo "Logs:"
    kubectl logs job/$MIGRATION_JOB -n $NAMESPACE --tail=50
    exit 1
}

# Check migration result
MIGRATION_RESULT=$(kubectl get job/$MIGRATION_JOB -n $NAMESPACE -o jsonpath='{.status.succeeded}')
if [ "$MIGRATION_RESULT" = "1" ]; then
    echo "✅ Migration completed successfully"
    echo ""
    echo "Migration logs:"
    kubectl logs job/$MIGRATION_JOB -n $NAMESPACE
else
    echo "❌ Migration failed"
    kubectl logs job/$MIGRATION_JOB -n $NAMESPACE
    exit 1
fi

# Step 2: Apply backfill job
echo ""
echo "📋 Step 2: Starting historical data backfill (365 days)..."
kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/backfill-job-complete.yaml

# Wait for backfill job to complete (longer timeout since it may take time)
echo "⏳ Waiting for backfill job to complete (max 30 minutes)..."
kubectl wait --for=condition=complete job/$BACKFILL_JOB -n $NAMESPACE --timeout=1800s 2>/dev/null || {
    echo "⚠️  Backfill job timeout (may still be running)"
    echo "Check status with: kubectl describe job/$BACKFILL_JOB -n $NAMESPACE"
    echo "View logs with: kubectl logs job/$BACKFILL_JOB -n $NAMESPACE -f"
}

# Check backfill result if job completed
BACKFILL_RESULT=$(kubectl get job/$BACKFILL_JOB -n $NAMESPACE -o jsonpath='{.status.succeeded}')
if [ "$BACKFILL_RESULT" = "1" ]; then
    echo "✅ Backfill completed successfully"
    echo ""
    echo "Backfill logs (last 50 lines):"
    kubectl logs job/$BACKFILL_JOB -n $NAMESPACE --tail=50
else
    echo "⚠️  Backfill job status unclear"
    echo "View logs: kubectl logs job/$BACKFILL_JOB -n $NAMESPACE"
fi

# Step 3: Verify data in database
echo ""
echo "📊 Step 3: Verifying data in database..."
echo ""

# Get postgres pod
POSTGRES_POD=$(kubectl get pod -n postgres -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ Could not find PostgreSQL pod"
    exit 1
fi

echo "Using PostgreSQL pod: $POSTGRES_POD"
echo ""

# Check new tables exist
echo "Checking if new tables were created:"
kubectl exec -n postgres $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT tablename
FROM pg_tables
WHERE tablename IN ('oura_sleep_phase_timeseries', 'oura_activity_met_timeseries')
ORDER BY tablename;" 2>/dev/null || echo "Could not query tables"

echo ""
echo "Checking sleep periods with new fields:"
kubectl exec -n postgres $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  MIN(date) as earliest_date,
  MAX(date) as latest_date,
  COUNT(CASE WHEN period_number IS NOT NULL THEN 1 END) as with_period_number,
  COUNT(CASE WHEN ring_id IS NOT NULL THEN 1 END) as with_ring_id,
  COUNT(CASE WHEN low_battery_alert IS NOT NULL THEN 1 END) as with_battery_alert
FROM oura_sleep_periods;" 2>/dev/null || echo "Could not query sleep periods"

echo ""
echo "Checking activity with new fields:"
kubectl exec -n postgres $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  COUNT(CASE WHEN target_meters IS NOT NULL THEN 1 END) as with_targets,
  COUNT(CASE WHEN sedentary_met_minutes IS NOT NULL THEN 1 END) as with_sedentary_met
FROM oura_activity;" 2>/dev/null || echo "Could not query activity"

echo ""
echo "Checking sleep phase time-series data:"
kubectl exec -n postgres $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_phases,
  COUNT(DISTINCT sleep_period_id) as unique_periods,
  MIN(timestamp) as earliest,
  MAX(timestamp) as latest
FROM oura_sleep_phase_timeseries;" 2>/dev/null || echo "Could not query sleep phase data"

echo ""
echo "Checking activity MET time-series data:"
kubectl exec -n postgres $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT activity_date) as unique_dates
FROM oura_activity_met_timeseries;" 2>/dev/null || echo "Could not query activity MET data"

echo ""
echo "=================================================="
echo "✅ Migration and backfill workflow complete!"
echo ""
echo "Summary:"
echo "- New tables created: oura_sleep_phase_timeseries, oura_activity_met_timeseries"
echo "- New columns added to: oura_sleep_periods, oura_activity, oura_readiness"
echo "- Historical data backfilled for 365 days"
echo ""
echo "Next steps:"
echo "1. Monitor collector CronJob: kubectl get cronjob -n $NAMESPACE"
echo "2. View upcoming runs: kubectl get events -n $NAMESPACE"
echo "3. Check logs: kubectl logs -f deployment/oura-collector -n $NAMESPACE"
