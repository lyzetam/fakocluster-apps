# Gitleaks - Secret Detection and Cleanup Service

## Overview

Gitleaks is an automated secret scanning and cleanup service deployed in the Fako cluster. It runs as a scheduled CronJob that scans Git repositories for exposed secrets, API keys, and sensitive information. When secrets are detected, it can automatically remove them from the entire Git history using BFG Repo-Cleaner. This service helps maintain security by preventing accidental exposure of credentials in version control.

## Key Features

- **Automated Scanning**: Scheduled scans every 6 hours
- **Secret Detection**: Identifies various types of secrets and credentials
- **History Cleanup**: Removes secrets from entire Git history
- **Dry Run Mode**: Test scans without making changes
- **Auto-Push**: Optional automatic pushing of cleaned repos
- **Slack Notifications**: Alerts when secrets are found
- **GitHub Integration**: Uses GitHub token for authentication
- **Comprehensive Reports**: JSON reports of findings

## Architecture

### Components

1. **CronJob**: Scheduled execution every 6 hours
2. **ServiceAccount**: For Kubernetes API access
3. **ConfigMap**: Cleanup script and configuration
4. **External Secret**: GitHub token from AWS Secrets Manager
5. **Init Container**: Installs required tools (BFG, Java)
6. **Volumes**: Temporary storage for scans and results

### Resource Requirements

- **Memory**: 512Mi (request), 1Gi (limit)
- **CPU**: 200m (request), 500m (limit)
- **Storage**: EmptyDir volumes for temporary data

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | From secret | GitHub authentication token |
| `DRY_RUN` | `false` | Run scan without cleanup |
| `AUTO_PUSH` | `false` | Auto-push cleaned repos |
| `SLACK_WEBHOOK` | Optional | Slack notification URL |
| `REPO_URL` | In script | Target repository URL |

### Schedule

- **CronJob Schedule**: `0 */6 * * *` (every 6 hours)
- Runs at: 00:00, 06:00, 12:00, 18:00 UTC

## Usage

### Manual Execution

Trigger a manual scan:
```bash
kubectl create job --from=cronjob/gitleaks-scanner manual-scan-$(date +%s) -n security-scanning
```

### Monitoring Scans

Watch job execution:
```bash
# List recent jobs
kubectl get jobs -n security-scanning --sort-by=.metadata.creationTimestamp

# Watch logs
kubectl logs -n security-scanning job/gitleaks-scanner-xxxxx -f
```

### Viewing Results

```bash
# Get scan results from completed job
kubectl cp security-scanning/gitleaks-scanner-xxxxx:/tmp/scan-results ./scan-results

# View cleanup report
cat scan-results/cleanup-report.json

# View detailed findings
cat scan-results/gitleaks-report.json
```

## Scan Process

### 1. Repository Clone
- Clones target repository with mirror mode
- Uses GitHub token for authentication
- Creates working copy for scanning

### 2. Secret Detection
- Runs Gitleaks against entire repository
- Generates JSON report of findings
- Identifies affected files and secrets

### 3. Report Generation
- Parses results for unique secrets
- Creates replacement mappings
- Generates summary statistics

### 4. Cleanup (if enabled)
- Uses BFG Repo-Cleaner
- Replaces secrets with `***REMOVED***`
- Cleans Git history completely
- Runs garbage collection

### 5. Push (if enabled)
- Force pushes cleaned repository
- Updates all branches and tags
- Sends completion notification

## Operations

### Enable/Disable Scanning

```bash
# Suspend CronJob
kubectl patch cronjob gitleaks-scanner -n security-scanning -p '{"spec":{"suspend":true}}'

# Resume CronJob
kubectl patch cronjob gitleaks-scanner -n security-scanning -p '{"spec":{"suspend":false}}'
```

### Changing Configuration

#### Switch to Production Mode
```bash
# Edit CronJob
kubectl edit cronjob gitleaks-scanner -n security-scanning

# Change:
# DRY_RUN: "false"
# AUTO_PUSH: "true"  # CAUTION: This will modify Git history
```

#### Update Schedule
```bash
# Change to daily at 2 AM
kubectl patch cronjob gitleaks-scanner -n security-scanning \
  -p '{"spec":{"schedule":"0 2 * * *"}}'
```

### Adding Repositories

Edit the ConfigMap to scan additional repos:
```bash
kubectl edit configmap gitleaks-cleanup-script -n security-scanning
```

## Troubleshooting

### Job Failures

1. **Check job status**:
```bash
kubectl describe job -n security-scanning gitleaks-scanner-xxxxx
```

2. **View pod logs**:
```bash
kubectl logs -n security-scanning job/gitleaks-scanner-xxxxx --all-containers
```

3. **Common issues**:
   - GitHub token expired
   - Repository access denied
   - Out of memory
   - Network connectivity

### GitHub Token Issues

1. **Verify secret exists**:
```bash
kubectl get secret github-credentials -n security-scanning
```

2. **Check token permissions**:
   - Needs repo scope for private repos
   - Needs write access for auto-push

3. **Update token**:
```bash
# Update in AWS Secrets Manager
# External Secret will sync automatically
```

### BFG/Java Issues

1. **Check init container**:
```bash
kubectl logs -n security-scanning job/gitleaks-scanner-xxxxx -c setup
```

2. **Verify BFG download**:
   - Check network connectivity
   - Verify Maven repository access

### Memory Issues

For large repositories:
```yaml
resources:
  limits:
    memory: "2Gi"  # Increase if needed
```

## Security Considerations

### Credentials
- GitHub token stored in AWS Secrets Manager
- No hardcoded secrets in configurations
- Token should have minimal required permissions

### Repository Access
- Use read-only tokens for scanning only
- Separate tokens for push operations
- Consider using GitHub Apps for better security

### Cleanup Safety
- Always test with DRY_RUN first
- Backup repositories before cleanup
- Understand Git history rewriting implications

### Best Practices
1. **Start with dry run**: Test before enabling cleanup
2. **Monitor notifications**: Set up Slack alerts
3. **Regular reviews**: Check scan reports weekly
4. **Coordinate cleanup**: Notify team before history rewrite
5. **Backup first**: Always backup before auto-push

## Gitleaks Configuration

### Custom Rules

Add custom detection rules:
```yaml
# .gitleaks.toml in repo
[[rules]]
description = "Custom API Key"
regex = '''company_api_key_[a-zA-Z0-9]{32}'''
tags = ["api", "custom"]
```

### Exclusions

Exclude false positives:
```toml
[allowlist]
paths = [
  "docs/examples",
  "test/fixtures"
]
files = [
  "go.sum",
  "package-lock.json"
]
```

## Integration Examples

### With CI/CD

Pre-commit hook:
```bash
#!/bin/bash
# .git/hooks/pre-commit
gitleaks detect --source . --verbose
```

### GitHub Actions
```yaml
name: Gitleaks
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: gitleaks/gitleaks-action@v2
```

### Slack Notifications

Configure rich notifications:
```json
{
  "text": "Gitleaks Scan Complete",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Secrets Found", "value": "5", "short": true},
      {"title": "Files Affected", "value": "3", "short": true}
    ]
  }]
}
```

## Monitoring

### Key Metrics
- Scan frequency and duration
- Number of secrets detected
- Cleanup success rate
- Repository scan coverage
- False positive rate

### Dashboards

Create monitoring dashboard:
```yaml
# ConfigMap for Grafana dashboard
apiVersion: v1
kind: ConfigMap
metadata:
  name: gitleaks-dashboard
data:
  dashboard.json: |
    {
      "title": "Gitleaks Security Scanning",
      "panels": [...]
    }
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Check for failed scans
   - Review new findings

2. **Weekly**:
   - Analyze trends
   - Update exclusion lists
   - Review false positives

3. **Monthly**:
   - Update Gitleaks version
   - Review scanning scope
   - Audit cleaned secrets

### Version Updates

```bash
# Update Gitleaks version
kubectl set image cronjob/gitleaks-scanner \
  gitleaks=zricethezav/gitleaks:v8.29.0 \
  -n security-scanning
```

### Backup Reports

Archive scan results:
```bash
#!/bin/bash
# backup-gitleaks-reports.sh
DATE=$(date +%Y%m%d)
kubectl cp security-scanning/gitleaks-scanner-xxxxx:/tmp/scan-results \
  /backups/gitleaks/$DATE/
```

## Recovery Procedures

### If Secrets Were Pushed

1. **Immediate actions**:
   - Rotate affected credentials
   - Run cleanup with AUTO_PUSH
   - Notify security team

2. **Follow-up**:
   - Audit access logs
   - Update security policies
   - Implement additional controls

### Repository Recovery

If cleanup causes issues:
```bash
# Restore from backup
git clone --mirror /backup/repo.git
git push --mirror https://github.com/org/repo.git
```

## Future Improvements

- [ ] Support multiple repositories per scan
- [ ] Integrate with GitHub Security Alerts
- [ ] Add support for GitLab/Bitbucket
- [ ] Implement incremental scanning
- [ ] Create web dashboard for results
- [ ] Add support for pre-receive hooks
- [ ] Implement secret rotation automation
- [ ] Add machine learning for false positive reduction
- [ ] Create remediation workflows
- [ ] Add support for container image scanning
