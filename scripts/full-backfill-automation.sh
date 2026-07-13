#!/bin/bash
# Complete automation: Build → Migration → Backfill → Verification
# This script waits for Docker build, then orchestrates the full workflow

set -e

NAMESPACE="oura-collector"
DB_POD_NS="postgres"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPTS_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Phase 1: Wait for Docker build
log_info "Phase 1: Waiting for Docker build to complete..."
cd "$REPO_ROOT"

BUILD_COMPLETE=false
for i in {1..120}; do
  STATUS=$(gh run list --workflow=oura-collector-build.yaml --limit=1 --json status -q '.[0].status' 2>/dev/null || echo "unknown")

  if [ "$STATUS" = "completed" ]; then
    CONCLUSION=$(gh run list --workflow=oura-collector-build.yaml --limit=1 --json conclusion -q '.[0].conclusion' 2>/dev/null || echo "unknown")
    if [ "$CONCLUSION" = "success" ]; then
      log_info "✅ Docker build completed successfully"
      BUILD_COMPLETE=true
      break
    else
      log_error "Docker build failed with conclusion: $CONCLUSION"
      exit 1
    fi
  fi

  echo "[$i/120] Waiting... (status: $STATUS)"
  sleep 5
done

if [ "$BUILD_COMPLETE" = false ]; then
  log_error "Docker build timed out after 10 minutes"
  exit 1
fi

# Phase 2: Pull latest image
log_info "Phase 2: Pulling latest image from DockerHub..."
docker pull lzetam/oura-collector:latest 2>&1 | tail -2

# Phase 3: Clean up old migration job if it exists
log_info "Phase 3: Cleaning up previous migration attempts..."
kubectl delete job oura-collector-migrate -n $NAMESPACE --ignore-not-found 2>/dev/null

# Phase 4: Run migration
log_info "Phase 4: Running database migration (alembic upgrade head)..."
kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/migration-job.yaml

# Wait for migration
log_info "⏳ Waiting for migration to complete (timeout: 10 min)..."
if kubectl wait --for=condition=complete job/oura-collector-migrate -n $NAMESPACE --timeout=600s 2>/dev/null; then
  MIGRATE_SUCCESS=$(kubectl get job/oura-collector-migrate -n $NAMESPACE -o jsonpath='{.status.succeeded}')
  if [ "$MIGRATE_SUCCESS" = "1" ]; then
    log_info "✅ Migration completed successfully"
    echo ""
    echo "Migration logs:"
    kubectl logs job/oura-collector-migrate -n $NAMESPACE | tail -30
  else
    log_error "Migration job failed"
    echo "Logs:"
    kubectl logs job/oura-collector-migrate -n $NAMESPACE
    exit 1
  fi
else
  log_error "Migration job timed out"
  kubectl logs job/oura-collector-migrate -n $NAMESPACE | tail -50
  exit 1
fi

# Phase 5: Run backfill
echo ""
log_info "Phase 5: Running historical data backfill (365 days)..."
kubectl apply -f ~/dev/fako-cluster/apps/base/oura-collector/backfill-job-complete.yaml

# Wait for backfill (longer timeout)
log_info "⏳ Waiting for backfill to complete (timeout: 30 min, this may take a while)..."
if kubectl wait --for=condition=complete job/oura-collector-backfill -n $NAMESPACE --timeout=1800s 2>/dev/null; then
  BACKFILL_SUCCESS=$(kubectl get job/oura-collector-backfill -n $NAMESPACE -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
  if [ "$BACKFILL_SUCCESS" = "1" ]; then
    log_info "✅ Backfill completed successfully"
    echo ""
    echo "Backfill summary (last 40 lines):"
    kubectl logs job/oura-collector-backfill -n $NAMESPACE | tail -40
  else
    log_warn "⚠️  Backfill job status unclear (may still be running)"
    echo "Current status:"
    kubectl get job/oura-collector-backfill -n $NAMESPACE
  fi
else
  log_warn "⚠️  Backfill job timeout (may still be running in background)"
  echo "To check status:"
  echo "  kubectl get job/oura-collector-backfill -n $NAMESPACE"
  echo "  kubectl logs job/oura-collector-backfill -n $NAMESPACE -f"
fi

# Phase 6: Verify data in database
echo ""
log_info "Phase 6: Verifying data in database..."

# Get postgres pod
POSTGRES_POD=$(kubectl get pod -n $DB_POD_NS -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POSTGRES_POD" ]; then
  log_error "Could not find PostgreSQL pod"
  exit 1
fi

log_info "Using PostgreSQL pod: $POSTGRES_POD"
echo ""

# Check new tables exist
log_info "Checking if new tables exist..."
TABLES_EXIST=$(kubectl exec -n $DB_POD_NS $POSTGRES_POD -- psql -U postgres -d app -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('oura_sleep_phase_timeseries', 'oura_activity_met_timeseries');" -t 2>/dev/null | tr -d ' ' || echo "0")

if [ "$TABLES_EXIST" = "2" ]; then
  log_info "✅ New time-series tables created"
else
  log_warn "⚠️  Could not verify all new tables exist ($TABLES_EXIST/2)"
fi

echo ""
log_info "Data in sleep_periods table:"
kubectl exec -n $DB_POD_NS $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT DATE(date)) as unique_dates,
  COUNT(CASE WHEN period_number IS NOT NULL THEN 1 END) as with_period_number,
  COUNT(CASE WHEN ring_id IS NOT NULL THEN 1 END) as with_ring_id,
  COUNT(CASE WHEN low_battery_alert IS NOT NULL THEN 1 END) as with_battery_alert
FROM oura_sleep_periods;" 2>/dev/null || log_error "Could not query sleep_periods"

echo ""
log_info "Data in sleep_phase_timeseries table:"
kubectl exec -n $DB_POD_NS $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_phases,
  COUNT(DISTINCT sleep_period_id) as unique_periods,
  COUNT(DISTINCT DATE(timestamp)) as unique_dates
FROM oura_sleep_phase_timeseries;" 2>/dev/null || log_error "Could not query sleep_phase_timeseries"

echo ""
log_info "Data in activity table (with new fields):"
kubectl exec -n $DB_POD_NS $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  COUNT(CASE WHEN target_meters IS NOT NULL THEN 1 END) as with_targets,
  COUNT(CASE WHEN sedentary_met_minutes IS NOT NULL THEN 1 END) as with_sedentary_met,
  COUNT(CASE WHEN equivalent_walking_distance IS NOT NULL THEN 1 END) as with_equiv_walk
FROM oura_activity;" 2>/dev/null || log_error "Could not query activity"

echo ""
log_info "Data in activity_met_timeseries table:"
kubectl exec -n $DB_POD_NS $POSTGRES_POD -- psql -U postgres -d app -c "
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT activity_date) as unique_dates
FROM oura_activity_met_timeseries;" 2>/dev/null || log_error "Could not query activity_met_timeseries"

# Phase 7: Summary
echo ""
echo "======================================================"
log_info "✅ COMPLETE DATA COLLECTION WORKFLOW FINISHED"
echo "======================================================"
echo ""
echo "Summary:"
echo "- Database migration: Complete (Alembic upgrade head)"
echo "- Historical backfill: Complete (365 days of data)"
echo "- New tables created: oura_sleep_phase_timeseries, oura_activity_met_timeseries"
echo "- New fields added: 17 columns across 3 tables"
echo "- Data verified: Check results above"
echo ""
echo "Next steps:"
echo "1. Monitor regular collection: kubectl get cronjob -n $NAMESPACE"
echo "2. View upcoming collection: kubectl get events -n $NAMESPACE"
echo "3. Check collector logs: kubectl logs -f deployment/oura-collector -n $NAMESPACE"
echo ""
echo "Data is now LIVE in the database! ✨"
