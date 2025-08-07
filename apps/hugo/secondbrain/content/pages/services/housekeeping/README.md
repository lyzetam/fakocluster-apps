# Housekeeping - Cluster Cleanup Service

## Overview

Housekeeping is an automated cluster maintenance service deployed in the Fako cluster. It runs as a CronJob that periodically cleans up completed and failed pods across all namespaces. This service helps maintain cluster hygiene by removing terminated pods that would otherwise accumulate and consume resources. It's essential for keeping the cluster clean and preventing resource exhaustion from leftover pod metadata.

## Key Features

- **Automated Cleanup**: Runs every hour to clean terminated pods
- **Cluster-Wide**: Scans all namespaces for cleanup candidates
- **Safe Deletion**: Only removes pods in Succeeded or Failed states
- **Detailed Logging**: Reports what was found and cleaned
- **Concurrency Control**: Prevents overlapping cleanup runs
- **Statistics Tracking**: Counts total pods found and deleted
- **Force Deletion**: Uses grace period 0 for immediate removal
- **Job History**: Keeps history of last 3 successful/failed runs

## Architecture

### Components

1. **CronJob**: Scheduled execution every hour
2. **ServiceAccount**: Cluster-wide permissions for pod management
3. **ClusterRole**: Permissions to list and delete pods
4. **ConfigMap**: Cleanup script with logic
5. **Container**: kubectl image with bash script execution

### Resource Requirements

- **Image**: `bitnami/kubectl:1.33`
- **CPU/Memory**: Minimal (kubectl operations)
- **Permissions**: Cluster-wide pod list/delete

## Configuration

### Schedule

- **CronJob Schedule**: `0 * * * *` (every hour at minute 0)
- **Concurrency Policy**: `Forbid` (no overlapping runs)
- **TTL After Finish**: 3600 seconds (1 hour)
- **History Limits**: 3 successful, 3 failed jobs

### Cleanup Targets

The service removes pods in these states:
- **Succeeded**: Completed jobs and one-time pods
- **Failed**: Crashed or errored pods

## Usage

### Manual Execution

Trigger immediate cleanup:
```bash
kubectl create job --from=cronjob/housekeeping manual-cleanup-$(date +%s) -n housekeeping
```

### Monitoring Cleanup

Watch cleanup progress:
```bash
# View current job
kubectl logs -n housekeeping -l app=housekeeping -f

# List recent jobs
kubectl get jobs -n housekeeping --sort-by=.metadata.creationTimestamp
```

### Viewing Statistics

Check cleanup history:
```bash
# Get logs from last successful job
kubectl logs -n housekeeping \
  $(kubectl get pods -n housekeeping -l app=housekeeping --sort-by=.metadata.creationTimestamp -o name | tail -1)
```

## Cleanup Process

### 1. Namespace Discovery
- Lists all namespaces in cluster
- Iterates through each namespace

### 2. Pod Identification
- Queries pods with status.phase == "Succeeded"
- Queries pods with status.phase == "Failed"
- Combines results for processing

### 3. Pod Details
- Retrieves pod age and phase
- Logs pod information before deletion

### 4. Force Deletion
- Deletes with grace-period=0
- Uses --force flag for immediate removal
- Tracks success/failure of each deletion

### 5. Statistics
- Counts total pods found
- Counts successfully deleted pods
- Reports summary at completion

## Operations

### Enable/Disable Cleanup

```bash
# Suspend housekeeping
kubectl patch cronjob housekeeping -n housekeeping -p '{"spec":{"suspend":true}}'

# Resume housekeeping
kubectl patch cronjob housekeeping -n housekeeping -p '{"spec":{"suspend":false}}'
```

### Adjust Schedule

```bash
# Change to every 30 minutes
kubectl patch cronjob housekeeping -n housekeeping \
  -p '{"spec":{"schedule":"*/30 * * * *"}}'

# Change to twice daily
kubectl patch cronjob housekeeping -n housekeeping \
  -p '{"spec":{"schedule":"0 2,14 * * *"}}'
```

### Exclude Namespaces

Edit the ConfigMap to exclude specific namespaces:
```bash
kubectl edit configmap housekeeping-script -n housekeeping
```

Add exclusion logic:
```bash
# Skip system namespaces
if [[ "$ns" =~ ^(kube-system|kube-public|kube-node-lease)$ ]]; then
    continue
fi
```

## Troubleshooting

### Job Failures

1. **Check job status**:
```bash
kubectl describe job -n housekeeping housekeeping-xxxxx
```

2. **View pod logs**:
```bash
kubectl logs -n housekeeping job/housekeeping-xxxxx
```

3. **Common issues**:
   - Permission denied (RBAC)
   - kubectl command failures
   - Script syntax errors

### Permission Issues

1. **Verify ServiceAccount**:
```bash
kubectl get sa housekeeping -n housekeeping
```

2. **Check ClusterRole**:
```bash
kubectl describe clusterrole housekeeping
```

3. **Test permissions**:
```bash
kubectl auth can-i delete pods --all-namespaces \
  --as=system:serviceaccount:housekeeping:housekeeping
```

### No Pods Being Cleaned

1. **Check for completed pods**:
```bash
kubectl get pods --all-namespaces --field-selector=status.phase=Succeeded
kubectl get pods --all-namespaces --field-selector=status.phase=Failed
```

2. **Verify jq installation**:
```bash
kubectl exec -n housekeeping deployment/housekeeping -- which jq
```

## Security Considerations

### RBAC Permissions
- Limited to pod list and delete operations
- No access to secrets or configmaps
- Cannot modify running pods

### Namespace Isolation
- Consider excluding sensitive namespaces
- Add namespace labels for filtering
- Implement allowlist/denylist

### Audit Trail
- All deletions logged in job output
- Kubernetes audit logs track API calls
- Consider external log aggregation

### Best Practices
1. **Test in staging**: Verify behavior before production
2. **Monitor closely**: Check logs after deployment
3. **Gradual rollout**: Start with specific namespaces
4. **Set alerts**: Monitor for failed cleanup jobs
5. **Regular review**: Audit what's being cleaned

## Customization

### Pod Age Filtering

Add age-based filtering:
```bash
# Only delete pods older than 24 hours
pod_age=$(kubectl get pod "$pod" -n "$namespace" \
  -o jsonpath='{.metadata.creationTimestamp}')
if [[ $(date -d "$pod_age" +%s) -lt $(date -d '24 hours ago' +%s) ]]; then
    kubectl delete pod "$pod" -n "$namespace"
fi
```

### Label-Based Filtering

Clean only labeled pods:
```bash
# Only clean pods with cleanup=true label
labeled_pods=$(kubectl get pods -n "$namespace" \
  -l cleanup=true \
  --field-selector=status.phase=Succeeded \
  -o jsonpath='{.items[*].metadata.name}')
```

### Custom Notifications

Add Slack notifications:
```bash
# Send summary to Slack
curl -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  -d "{\"text\":\"Housekeeping: Cleaned $TOTAL_DELETED pods from $namespace_count namespaces\"}"
```

## Monitoring

### Key Metrics
- Pods cleaned per run
- Namespaces processed
- Cleanup duration
- Failed deletions
- Job success rate

### Prometheus Metrics

Add metrics exporter:
```yaml
# Add pushgateway container
- name: metrics
  image: prom/pushgateway
  ports:
  - containerPort: 9091
```

Push metrics from script:
```bash
# Push to Prometheus
echo "housekeeping_pods_deleted $TOTAL_DELETED" | \
  curl --data-binary @- http://localhost:9091/metrics/job/housekeeping
```

### Grafana Dashboard

Key panels:
- Pods cleaned over time
- Cleanup job duration
- Failed cleanup attempts
- Namespace distribution

## Integration Examples

### With Monitoring Stack

Alert on cleanup failures:
```yaml
# PrometheusRule
- alert: HousekeepingFailed
  expr: kube_job_status_failed{job_name=~"housekeeping-.*"} > 0
  for: 1h
  annotations:
    summary: "Housekeeping job failed"
```

### With CI/CD

Trigger cleanup after deployments:
```yaml
# In deployment pipeline
- name: Trigger housekeeping
  run: |
    kubectl create job --from=cronjob/housekeeping \
      post-deploy-cleanup-${{ github.run_id }} \
      -n housekeeping
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Review cleanup logs
   - Check for failed jobs

2. **Weekly**:
   - Analyze cleanup patterns
   - Review excluded namespaces
   - Check resource usage

3. **Monthly**:
   - Update kubectl version
   - Review RBAC permissions
   - Optimize cleanup logic

### Performance Tuning

For large clusters:
```bash
# Parallel namespace processing
for ns in $namespaces; do
    cleanup_namespace "$ns" &
done
wait
```

### Backup Considerations

Before major changes:
```bash
# Export current configuration
kubectl get cronjob housekeeping -n housekeeping -o yaml > housekeeping-backup.yaml
kubectl get cm housekeeping-script -n housekeeping -o yaml > script-backup.yaml
```

## Advanced Features

### Multi-Resource Cleanup

Extend to clean other resources:
```bash
# Clean completed jobs
kubectl delete jobs --all-namespaces \
  --field-selector status.successful=1

# Clean old replicasets
kubectl get rs --all-namespaces -o json | \
  jq -r '.items[] | select(.spec.replicas == 0) | 
  "\(.metadata.namespace) \(.metadata.name)"' | \
  while read ns rs; do
    kubectl delete rs "$rs" -n "$ns"
  done
```

### Intelligent Cleanup

Add smart filtering:
```bash
# Keep recent failures for debugging
if [[ "$phase" == "Failed" ]]; then
    # Keep failures from last 24 hours
    if [[ $(date -d "$age" +%s) -gt $(date -d '24 hours ago' +%s) ]]; then
        echo "    Keeping recent failure for debugging"
        continue
    fi
fi
```

## Future Improvements

- [ ] Add configurable retention policies
- [ ] Implement namespace exclusion via labels
- [ ] Add support for cleaning other resources
- [ ] Create web dashboard for statistics
- [ ] Implement dry-run mode
- [ ] Add email notifications
- [ ] Support custom cleanup rules
- [ ] Add PVC cleanup for orphaned volumes
- [ ] Implement gradual deletion (rate limiting)
- [ ] Add cost savings calculations
