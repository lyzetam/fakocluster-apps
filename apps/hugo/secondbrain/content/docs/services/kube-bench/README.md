# Kube-bench - Kubernetes Security Benchmark Scanner

## Overview

Kube-bench is an automated security compliance scanner deployed in the Fako cluster. It runs the CIS Kubernetes Benchmark checks to ensure the cluster follows security best practices. The service executes as a daily CronJob that performs comprehensive security scans, checking configurations of various Kubernetes components against industry standards. Results are saved with timestamps for audit trails and compliance reporting.

## Key Features

- **CIS Benchmark Compliance**: Checks against Center for Internet Security standards
- **Automated Scanning**: Daily scheduled security assessments
- **Comprehensive Coverage**: Scans master and worker node configurations
- **JSON Output**: Machine-readable results for integration
- **Historical Records**: Timestamped results for trend analysis
- **Host Access**: Direct access to Kubernetes configuration files
- **Multi-Component**: Checks etcd, kubelet, API server, and more
- **Results Processing**: Automatic display of scan findings

## Architecture

### Components

1. **CronJob**: Daily execution at 2 AM
2. **ServiceAccount**: Permissions for scanning operations
3. **Main Container**: kube-bench scanner with host access
4. **Results Processor**: Monitors and displays scan results
5. **Storage**: PersistentVolumeClaim for scan history
6. **Host Mounts**: Access to Kubernetes system directories

### Resource Requirements

- **Scanner**: 256Mi RAM (request), 512Mi (limit)
- **Processor**: 64Mi RAM (request), 128Mi (limit)
- **CPU**: 100m-300m for scanner, 50m-100m for processor
- **Storage**: Persistent volume for results history

## Configuration

### Schedule

- **CronJob Schedule**: `0 2 * * *` (daily at 2:00 AM)
- **Concurrency Policy**: `Forbid` (no overlapping scans)
- **History Limits**: 3 successful, 3 failed jobs

### Security Context

- **hostPID**: `true` (access host processes)
- **privileged**: `true` (full host access)
- **Read-only mounts**: All host paths mounted read-only

## Usage

### Manual Scan Execution

Trigger an immediate security scan:
```bash
kubectl create job --from=cronjob/kube-bench-scanner manual-scan-$(date +%s) -n kube-bench
```

### Viewing Scan Results

Latest results:
```bash
# List result files
kubectl exec -n kube-bench deployment/results-viewer -- ls -la /results/

# View latest scan
kubectl exec -n kube-bench deployment/results-viewer -- \
  cat $(ls -t /results/kube-bench-results-*.json | head -1)
```

Copy results locally:
```bash
# Get pod name
POD=$(kubectl get pods -n kube-bench -l app.kubernetes.io/name=kube-bench -o name | head -1)

# Copy results
kubectl cp -n kube-bench $POD:/results ./kube-bench-results/
```

### Monitoring Scans

Watch scan execution:
```bash
# Watch job progress
kubectl logs -n kube-bench -l app.kubernetes.io/name=kube-bench -f

# Check job status
kubectl get jobs -n kube-bench --sort-by=.metadata.creationTimestamp
```

## Scan Results

### Result Structure

JSON output includes:
```json
{
  "Controls": [
    {
      "id": "1",
      "text": "Control Plane Security Configuration",
      "tests": [
        {
          "id": "1.1.1",
          "desc": "Ensure API server pod specification permissions",
          "audit": "stat -c %a /etc/kubernetes/manifests/kube-apiserver.yaml",
          "pass": true,
          "scored": true
        }
      ]
    }
  ],
  "Totals": {
    "total_pass": 45,
    "total_fail": 5,
    "total_warn": 10,
    "total_info": 3
  }
}
```

### Common Checks

1. **Control Plane Components**:
   - API Server configuration
   - Controller Manager settings
   - Scheduler security
   - etcd data encryption

2. **Worker Node Security**:
   - Kubelet configuration
   - Kernel parameters
   - Network policies
   - Container runtime

3. **Policies**:
   - RBAC settings
   - Pod Security Standards
   - Network segmentation
   - Admission controllers

## Operations

### Analyzing Results

Parse JSON for failures:
```bash
# Extract failed checks
kubectl exec -n kube-bench deployment/results-viewer -- \
  jq '.Controls[].tests[] | select(.pass == false)' \
  /results/kube-bench-results-latest.json
```

Generate summary report:
```bash
# Get totals
kubectl exec -n kube-bench deployment/results-viewer -- \
  jq '.Totals' /results/kube-bench-results-latest.json
```

### Scheduling Changes

Modify scan frequency:
```bash
# Change to weekly (Sundays at 3 AM)
kubectl patch cronjob kube-bench-scanner -n kube-bench \
  -p '{"spec":{"schedule":"0 3 * * 0"}}'

# Change to twice daily
kubectl patch cronjob kube-bench-scanner -n kube-bench \
  -p '{"spec":{"schedule":"0 2,14 * * *"}}'
```

### Result Retention

Clean old results:
```bash
# Delete results older than 30 days
kubectl exec -n kube-bench deployment/results-viewer -- \
  find /results -name "*.json" -mtime +30 -delete
```

## Troubleshooting

### Scan Failures

1. **Check job status**:
```bash
kubectl describe job -n kube-bench kube-bench-scanner-xxxxx
```

2. **View pod logs**:
```bash
kubectl logs -n kube-bench job/kube-bench-scanner-xxxxx -c kube-bench
```

3. **Common issues**:
   - Missing host paths
   - Insufficient permissions
   - Node selector mismatch
   - PVC mount failures

### Permission Issues

1. **Verify ServiceAccount**:
```bash
kubectl get sa kube-bench -n kube-bench
kubectl describe clusterrolebinding kube-bench
```

2. **Check host access**:
```bash
# Test host path access
kubectl exec -n kube-bench $POD -c kube-bench -- ls -la /etc/kubernetes/
```

### No Results Generated

1. **Check result directory**:
```bash
kubectl exec -n kube-bench $POD -c results-processor -- ls -la /results/
```

2. **Verify write permissions**:
```bash
kubectl exec -n kube-bench $POD -c kube-bench -- touch /results/test.txt
```

## Security Considerations

### Privileged Access
- Requires privileged mode for host access
- Uses hostPID to see all processes
- Read-only mounts minimize risk

### RBAC Limitations
- ServiceAccount has minimal cluster permissions
- No write access to configuration
- Cannot modify cluster state

### Result Security
- Results may contain sensitive configuration details
- Store in secure PVC
- Limit access to kube-bench namespace

### Best Practices
1. **Review permissions**: Audit RBAC regularly
2. **Secure results**: Encrypt PVC if possible
3. **Monitor access**: Log who views results
4. **Act on findings**: Address failures promptly
5. **Version control**: Track remediation changes

## Remediation

### Common Fixes

#### API Server Hardening
```bash
# Example: Enable audit logging
--audit-log-maxage=30
--audit-log-maxbackup=3
--audit-log-maxsize=100
--audit-log-path=/var/log/audit.log
```

#### Kubelet Security
```yaml
# kubelet-config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
authentication:
  anonymous:
    enabled: false
authorization:
  mode: Webhook
```

#### etcd Encryption
```yaml
# encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-secret>
```

### Tracking Remediation

Create remediation records:
```bash
# Save remediation notes
kubectl create configmap kube-bench-remediation \
  --from-file=remediation-$(date +%Y%m%d).md \
  -n kube-bench
```

## Integration Examples

### With Monitoring

Prometheus alerts:
```yaml
# Alert on failed checks increasing
- alert: KubeBenchFailuresIncreasing
  expr: kube_bench_total_fail > kube_bench_total_fail offset 1d
  annotations:
    summary: "Security failures increased"
```

### CI/CD Pipeline

Pre-deployment check:
```yaml
# .gitlab-ci.yml
security-scan:
  script:
    - kubectl create job --from=cronjob/kube-bench-scanner ci-scan-$CI_JOB_ID
    - kubectl wait --for=condition=complete job/ci-scan-$CI_JOB_ID
    - kubectl logs job/ci-scan-$CI_JOB_ID
```

### Slack Notifications

Add notification script:
```bash
# In results-processor
FAILURES=$(jq '.Totals.total_fail' $LATEST_FILE)
if [ "$FAILURES" -gt 0 ]; then
  curl -X POST $SLACK_WEBHOOK \
    -d "{\"text\":\"Kube-bench: $FAILURES security failures detected\"}"
fi
```

## Monitoring

### Key Metrics
- Total pass/fail/warn counts
- Scan execution time
- Failure trends over time
- Most common failures
- Remediation progress

### Grafana Dashboard

Essential panels:
- Security score over time
- Failed checks by category
- Remediation timeline
- Compliance percentage

### Reports

Generate compliance report:
```bash
#!/bin/bash
# compliance-report.sh
LATEST=$(ls -t /results/kube-bench-results-*.json | head -1)
echo "# Kubernetes Security Compliance Report"
echo "Date: $(date)"
echo ""
echo "## Summary"
jq -r '.Totals | "- Passed: \(.total_pass)\n- Failed: \(.total_fail)\n- Warnings: \(.total_warn)"' $LATEST
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Review scan results
   - Check for new failures

2. **Weekly**:
   - Analyze failure trends
   - Plan remediation work
   - Clean old results

3. **Monthly**:
   - Update kube-bench version
   - Review benchmark changes
   - Generate compliance reports

### Version Updates

```bash
# Update to latest version
kubectl set image cronjob/kube-bench-scanner \
  kube-bench=aquasec/kube-bench:latest \
  -n kube-bench
```

### Benchmark Updates

Monitor CIS releases:
- Check for new benchmark versions
- Review changed requirements
- Update scan configuration

## Advanced Configuration

### Custom Checks

Add custom security checks:
```yaml
# custom-checks.yaml
groups:
- id: "custom"
  text: "Custom Security Checks"
  checks:
  - id: "C.1"
    text: "Custom network policy check"
    audit: "kubectl get netpol --all-namespaces"
```

### Selective Scanning

Run specific check groups:
```bash
kube-bench --targets=master --check=1.1
```

### Output Formats

Different output options:
```bash
# Plain text
kube-bench --outputfile /results/report.txt

# JUnit for CI
kube-bench --junit --outputfile /results/junit.xml
```

## Future Improvements

- [ ] Implement automated remediation for safe fixes
- [ ] Add trend analysis and reporting
- [ ] Create web dashboard for results
- [ ] Integrate with ticketing system
- [ ] Add email notifications
- [ ] Support multiple cluster scanning
- [ ] Implement custom policy engine
- [ ] Add compliance scoring system
- [ ] Create remediation playbooks
- [ ] Add cost of non-compliance metrics
