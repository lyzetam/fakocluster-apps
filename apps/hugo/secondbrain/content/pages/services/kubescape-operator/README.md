# Kubescape Operator - Kubernetes Security Scanning Platform

## Overview

Kubescape Operator is a comprehensive Kubernetes security scanning platform deployed in the Fako cluster. It provides continuous security assessment using multiple frameworks including NSA, MITRE, and CIS benchmarks. The operator performs real-time vulnerability scanning, compliance checking, and network policy analysis. It stores scan results locally and can optionally integrate with Kubescape Cloud for enhanced dashboards and reporting.

## Key Features

- **Multi-Framework Scanning**: NSA, MITRE, CIS compliance checks
- **Continuous Monitoring**: Real-time security posture assessment
- **Vulnerability Scanning**: Container image vulnerability detection
- **Network Policy Analysis**: Automated network policy recommendations
- **Local Storage**: Persistent storage for scan results and vulnerability DB
- **Prometheus Metrics**: Export security metrics for monitoring
- **Node Agent**: Runtime security monitoring on Linux nodes
- **Scheduled Scans**: Configurable scanning intervals

## Architecture

### Components

1. **Operator**: Core controller managing scans
2. **Kubevuln**: Vulnerability scanner component
3. **Gateway**: API gateway for results
4. **Node Agent**: Runtime security on each node
5. **Storage**: NFS-backed persistent volumes
6. **Helm Release**: Managed by Flux

### Resource Requirements

| Component | Memory Request | Memory Limit | CPU Request | CPU Limit | Ephemeral Storage |
|-----------|---------------|--------------|-------------|-----------|-------------------|
| Operator | 256Mi | 512Mi | 100m | 500m | 1Gi/2Gi |
| Kubevuln | 512Mi | 1Gi | 200m | 500m | 5Gi/15Gi |
| Gateway | 256Mi | 512Mi | 100m | 300m | 1Gi/2Gi |

## Configuration

### Scanning Schedule

| Framework | Schedule | Description |
|-----------|----------|-------------|
| NSA | Every 6 hours | National Security Agency guidelines |
| MITRE | Every 6 hours | MITRE ATT&CK framework |
| CIS v1.23 | Daily at 2 AM | Center for Internet Security benchmark |

### Storage Configuration

- **Scan Results**: 20Gi on `nfs-security-logs`
- **Vulnerability DB**: 10Gi on `nfs-security-logs`
- **Access Mode**: ReadWriteOnce

## Usage

### Viewing Scan Results

Access scan results via kubectl:
```bash
# List recent scans
kubectl get configurationscansummaries -n kubescape

# View detailed scan results
kubectl describe configurationscansummary <scan-name> -n kubescape

# Get vulnerability reports
kubectl get vulnerabilitymanifestsummaries -n kubescape
```

### Manual Scan Trigger

Trigger immediate scan:
```bash
# Scan with specific framework
kubectl exec -n kubescape deployment/kubescape-operator -- \
  kubescape scan framework nsa --submit

# Full cluster scan
kubectl exec -n kubescape deployment/kubescape-operator -- \
  kubescape scan framework all --submit
```

### Viewing Network Policies

Generated network policies:
```bash
# List generated policies
kubectl get generatednetworkpolicies -n kubescape

# View policy recommendations
kubectl describe generatednetworkpolicy <policy-name> -n kubescape
```

## Operations

### Monitoring Health

```bash
# Check operator status
kubectl get pods -n kubescape

# View operator logs
kubectl logs -n kubescape deployment/kubescape-operator

# Check vulnerability scanner
kubectl logs -n kubescape deployment/kubevuln
```

### Metrics Access

Prometheus metrics endpoint:
```bash
# Port forward to access metrics
kubectl port-forward -n kubescape svc/kubescape-metrics 9090:9090

# View metrics
curl http://localhost:9090/metrics
```

### Storage Management

Monitor storage usage:
```bash
# Check PVC usage
kubectl get pvc -n kubescape

# View storage details
kubectl exec -n kubescape deployment/kubevuln -- df -h /data
```

## Troubleshooting

### Pod Evictions

Common issue: kubevuln pod evicted due to ephemeral storage
```bash
# Check pod status
kubectl describe pod -n kubescape -l app=kubevuln

# If evicted, check events
kubectl get events -n kubescape --sort-by='.lastTimestamp'

# Solution: Already configured with 15Gi ephemeral storage limit
```

### Scan Failures

1. **Check scan job logs**:
```bash
kubectl logs -n kubescape -l job-name=<scan-job-name>
```

2. **Verify RBAC permissions**:
```bash
kubectl auth can-i --list \
  --as=system:serviceaccount:kubescape:kubescape-operator
```

3. **Check storage availability**:
```bash
kubectl describe pvc -n kubescape
```

### Node Agent Issues

1. **Verify node compatibility**:
```bash
# Check kernel version (needs BTF support)
kubectl get nodes -o wide

# Check node agent pods
kubectl get pods -n kubescape -l app=node-agent -o wide
```

2. **macOS exclusion**:
   - Node agent automatically excluded from macOS nodes
   - Only runs on Linux nodes with BTF support

## Security Frameworks

### NSA Framework
- Kubernetes Hardening Guidance
- Network segmentation checks
- Pod security standards
- RBAC configuration

### MITRE ATT&CK
- Threat modeling based on ATT&CK matrix
- Technique detection
- Lateral movement prevention
- Persistence mechanisms

### CIS Benchmarks
- Kubernetes CIS v1.23 compliance
- Control plane security
- Worker node hardening
- Network policies

## Best Practices

### Scan Result Analysis

1. **Priority-based remediation**:
   - Critical findings first
   - High-impact, low-effort fixes
   - Systematic approach

2. **Regular review cycle**:
   - Daily critical findings
   - Weekly compliance reports
   - Monthly trend analysis

3. **Exception management**:
   - Document accepted risks
   - Create exclusion rules
   - Regular review of exceptions

### Performance Optimization

1. **Scan scheduling**:
   - Avoid peak hours
   - Stagger framework scans
   - Balance coverage vs load

2. **Resource allocation**:
   - Monitor scanner performance
   - Adjust limits if needed
   - Use node affinity for dedicated scanning

### Integration

With CI/CD:
```yaml
# GitLab CI example
security-scan:
  script:
    - kubescape scan framework nsa --fail-threshold 70
```

With monitoring:
```yaml
# Prometheus alert
- alert: HighSecurityFindings
  expr: kubescape_scan_result_failed_resources > 10
  annotations:
    summary: "High number of security findings"
```

## Monitoring

### Key Metrics

- `kubescape_scan_result_failed_resources`: Failed resources per scan
- `kubescape_scan_result_total_resources`: Total scanned resources
- `kubescape_scan_duration_seconds`: Scan completion time
- `kubescape_vulnerability_summary_high`: High severity vulnerabilities
- `kubescape_compliance_score`: Overall compliance percentage

### Dashboards

Create Grafana dashboard:
```json
{
  "dashboard": {
    "title": "Kubescape Security",
    "panels": [
      {
        "title": "Compliance Score",
        "targets": [{
          "expr": "kubescape_compliance_score"
        }]
      }
    ]
  }
}
```

### Alerts

Configure critical alerts:
```yaml
# Critical vulnerability alert
- alert: CriticalVulnerability
  expr: kubescape_vulnerability_summary_critical > 0
  for: 5m
  annotations:
    summary: "Critical vulnerability detected"
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Review critical findings
   - Check scan completion
   - Monitor pod health

2. **Weekly**:
   - Analyze compliance trends
   - Update exclusion rules
   - Review network policies

3. **Monthly**:
   - Update operator version
   - Clean old scan results
   - Performance analysis

### Version Updates

```bash
# Update Helm release
kubectl edit helmrelease kubescape-operator -n kubescape

# Change version
spec:
  chart:
    spec:
      version: "1.x.x"  # New version
```

### Database Maintenance

Clean old scan results:
```bash
# Remove scans older than 30 days
kubectl exec -n kubescape deployment/kubescape-operator -- \
  find /data/scans -mtime +30 -delete
```

## Advanced Configuration

### Custom Scanning Rules

Add custom controls:
```yaml
# custom-control.yaml
apiVersion: kubescape.io/v1
kind: Control
metadata:
  name: custom-control
spec:
  rules:
    - name: "Check custom annotation"
      match:
        any:
        - resources:
            kinds: ["Deployment"]
```

### Scan Exclusions

Configure exclusions:
```yaml
# In values
scanExclusions:
  namespaces:
    - kube-system
    - kube-public
  resources:
    - name: "sensitive-deployment"
      namespace: "production"
```

### Cloud Integration

Enable Kubescape Cloud:
```yaml
kubescapeCloud:
  enabled: true
  account: "your-account-id"
  clusterName: "fako-cluster"
```

## Compliance Reporting

### Generate Reports

```bash
# Generate compliance report
kubectl exec -n kubescape deployment/kubescape-operator -- \
  kubescape scan framework cis --format pdf --output /tmp/report.pdf

# Copy report
kubectl cp kubescape/operator-pod:/tmp/report.pdf ./cis-compliance.pdf
```

### Automated Reporting

Create CronJob for reports:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: compliance-reporter
spec:
  schedule: "0 8 * * 1"  # Weekly Monday 8 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: reporter
            image: kubescape/kubescape
            command: ["generate-report.sh"]
```

## Future Improvements

- [ ] Integrate with ticketing system for findings
- [ ] Implement automated remediation for safe fixes
- [ ] Add custom framework for organization policies
- [ ] Create security scorecard dashboard
- [ ] Implement drift detection
- [ ] Add container signing verification
- [ ] Create remediation playbooks
- [ ] Implement security baseline enforcement
- [ ] Add integration with SIEM systems
- [ ] Create multi-cluster security dashboard
