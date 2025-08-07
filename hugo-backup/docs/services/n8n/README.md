# N8N Workflow Automation Service

## Overview

N8N is an open-source workflow automation tool deployed in the Fako cluster. It provides a visual interface for creating complex automation workflows, integrating with hundreds of services and APIs. N8N allows you to automate repetitive tasks, connect different services, and build sophisticated data pipelines without extensive coding.

## Key Features

- **Visual Workflow Builder**: Drag-and-drop interface for creating automations
- **200+ Integrations**: Pre-built nodes for popular services
- **Self-Hosted**: Full control over your data and workflows
- **PostgreSQL Backend**: Reliable storage using the cluster's PostgreSQL
- **Webhook Support**: Trigger workflows via HTTP webhooks
- **Custom Functions**: JavaScript code support for complex logic
- **Fair-Code License**: Source available with sustainable business model

## Architecture

### Components

1. **Deployment**: Single-replica deployment (stateful workflows)
2. **Service**: ClusterIP service on port 5678
3. **Ingress**: HTTPS access at `n8n.landryzetam.net`
4. **Storage**: PersistentVolumeClaim for workflow data
5. **Database**: PostgreSQL for workflow definitions and execution data
6. **External Secrets**: Database credentials from AWS Secrets Manager

### Resource Requirements

- **Memory**: 512Mi (request), 2Gi (limit)
- **CPU**: 250m (request), 1000m (limit)
- **Storage**: Persistent volume for N8N data and files
- **Database**: Uses shared PostgreSQL cluster

## Configuration

### Environment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `N8N_HOST` | `n8n.landryzetam.net` | External hostname |
| `N8N_PORT` | `5678` | Application port |
| `N8N_PROTOCOL` | `https` | External protocol |
| `WEBHOOK_URL` | `https://n8n.landryzetam.net/` | Webhook base URL |
| `GENERIC_TIMEZONE` | `America/New_York` | Timezone for scheduling |
| `N8N_METRICS` | `true` | Enable metrics endpoint |
| `N8N_TEMPLATES_ENABLED` | `true` | Enable workflow templates |

### Database Configuration

- **Type**: PostgreSQL
- **Host**: `postgres-cluster-rw.postgres.svc.cluster.local`
- **Database**: `app`
- **User**: `app`
- **Password**: Managed via External Secrets

## Usage

### Accessing N8N

External access:
```
https://n8n.landryzetam.net
```

Internal access:
```
http://n8n.n8n.svc.cluster.local:5678
```

### Initial Setup

1. **Access the UI**: Navigate to `https://n8n.landryzetam.net`
2. **Create admin account**: First user becomes admin
3. **Configure SMTP** (optional): For email notifications
4. **Set up credentials**: Store API keys for integrations

### Creating Your First Workflow

1. **Start with a trigger**:
   - Webhook
   - Schedule (Cron)
   - Manual trigger

2. **Add nodes**:
   - HTTP Request
   - Database operations
   - Data transformation
   - Service integrations

3. **Test and activate**:
   - Use test data
   - Check execution logs
   - Activate for production

### Common Use Cases

#### Webhook to Database
```javascript
// Example: Store webhook data in PostgreSQL
1. Webhook trigger node
2. Set node (transform data)
3. Postgres node (insert data)
```

#### Scheduled Data Sync
```javascript
// Example: Daily data sync
1. Cron trigger (0 2 * * *)
2. HTTP Request (fetch data)
3. IF node (check conditions)
4. Update multiple services
```

#### Error Notification
```javascript
// Example: Alert on failures
1. Error trigger
2. Format message
3. Send to Slack/Email
```

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n n8n

# View logs
kubectl logs -n n8n deployment/n8n

# Check health endpoint
kubectl exec -n n8n deployment/n8n -- curl -s http://localhost:5678/healthz
```

### Managing Workflows

#### Export Workflows
```bash
# Connect to pod
kubectl exec -it -n n8n deployment/n8n -- /bin/sh

# Export all workflows
n8n export:workflow --all --output=/tmp/workflows.json

# Copy to local
kubectl cp n8n/n8n-pod:/tmp/workflows.json ./n8n-workflows-backup.json
```

#### Import Workflows
```bash
# Copy file to pod
kubectl cp ./workflows.json n8n/n8n-pod:/tmp/workflows.json

# Import workflows
kubectl exec -n n8n deployment/n8n -- n8n import:workflow --input=/tmp/workflows.json
```

### Database Management

#### Check Workflow Count
```bash
kubectl exec -n postgres postgres-cluster-1 -- psql -U app -d app -c \
  "SELECT COUNT(*) FROM n8n.workflow_entity WHERE active = true;"
```

#### View Execution History
```bash
kubectl exec -n postgres postgres-cluster-1 -- psql -U app -d app -c \
  "SELECT id, finished, mode, startedAt, stoppedAt, workflowId 
   FROM n8n.execution_entity 
   ORDER BY startedAt DESC 
   LIMIT 10;"
```

## Troubleshooting

### Pod Not Starting

1. **Check logs**:
```bash
kubectl logs -n n8n deployment/n8n
```

2. **Verify database connection**:
```bash
kubectl exec -n n8n deployment/n8n -- nc -zv postgres-cluster-rw.postgres.svc.cluster.local 5432
```

3. **Check secrets**:
```bash
kubectl get secret -n n8n app-user-secret
```

### Workflow Execution Failures

1. **Check execution logs**:
   - UI: Executions → Failed executions
   - Click on execution for details

2. **Common issues**:
   - API credentials expired
   - Rate limits exceeded
   - Network timeouts
   - Invalid data formats

3. **Debug mode**:
   - Set `N8N_LOG_LEVEL=debug`
   - Restart pod
   - Check detailed logs

### Performance Issues

1. **Check resource usage**:
```bash
kubectl top pod -n n8n
```

2. **Database queries**:
```sql
-- Long-running executions
SELECT workflow_id, started_at, 
       EXTRACT(EPOCH FROM (NOW() - started_at)) as duration_seconds
FROM n8n.execution_entity
WHERE finished = false
ORDER BY started_at;
```

3. **Optimization tips**:
   - Limit workflow complexity
   - Use batching for large datasets
   - Implement error handling
   - Clean old executions regularly

### Webhook Issues

1. **Test webhook endpoint**:
```bash
curl -X POST https://n8n.landryzetam.net/webhook-test/your-webhook-id \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

2. **Check ingress**:
```bash
kubectl describe ingress n8n -n n8n
```

## Security Considerations

### Authentication
- First user registration creates admin
- Subsequent users need invitation
- Consider SSO integration with Keycloak

### API Security
- Store credentials encrypted in N8N
- Use environment variables for sensitive data
- Rotate API keys regularly

### Network Security
- Internal services only accessible within cluster
- HTTPS for external access
- Consider IP whitelisting for webhooks

### Best Practices
1. **Least privilege**: Create service accounts with minimal permissions
2. **Audit workflows**: Review automation logic regularly
3. **Input validation**: Sanitize webhook inputs
4. **Error handling**: Implement proper error workflows
5. **Backup workflows**: Regular exports to version control

## Monitoring

### Key Metrics
- Active workflow count
- Execution success/failure rate
- Execution duration
- Webhook response times
- Database connection pool usage
- Memory and CPU utilization

### Prometheus Metrics

N8N exposes metrics at `/metrics`:
```bash
# Example metrics
n8n_workflow_executions_total
n8n_workflow_execution_duration_seconds
n8n_workflow_execution_errors_total
```

### Grafana Dashboard

Create custom dashboard with:
- Execution trends
- Error rates by workflow
- Resource usage
- Database query performance

## Integration Examples

### Slack Notification
```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "alert-webhook"
    },
    {
      "name": "Slack",
      "type": "n8n-nodes-base.slack",
      "position": [450, 300],
      "credentials": {
        "slackApi": "Slack Account"
      },
      "parameters": {
        "channel": "#alerts",
        "text": "=Alert: {{$json[\"message\"]}}"
      }
    }
  ]
}
```

### Database to API Sync
```javascript
// Sync PostgreSQL data to external API
1. Cron node: "0 */6 * * *"
2. Postgres node: SELECT query
3. Loop over items
4. HTTP Request: POST to API
5. Update sync status in DB
```

### Multi-Service Integration
```javascript
// GitHub → Jira → Slack workflow
1. GitHub webhook (on PR)
2. Create Jira ticket
3. Notify Slack channel
4. Update GitHub PR with Jira link
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor failed executions
   - Check webhook availability

2. **Weekly**:
   - Review resource usage
   - Clean old execution data
   - Backup active workflows

3. **Monthly**:
   - Update N8N version
   - Audit workflow permissions
   - Review integration credentials

### Cleanup Old Executions

```sql
-- Delete executions older than 30 days
DELETE FROM n8n.execution_entity 
WHERE finished = true 
AND "stoppedAt" < NOW() - INTERVAL '30 days';
```

### Upgrade Procedure

1. **Backup workflows and credentials**
2. **Test new version in staging**
3. **Update deployment**:
```yaml
image: n8nio/n8n:1.107.0
```
4. **Monitor for issues**

## Performance Optimization

### Workflow Design
- Use Sub-workflows for reusable logic
- Implement pagination for large datasets
- Add error handling nodes
- Use code nodes for complex transformations

### Database Optimization
- Regular VACUUM on execution tables
- Index frequently queried columns
- Monitor table growth

### Resource Tuning
```yaml
# For heavy workloads
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Future Improvements

- [ ] Implement high availability setup
- [ ] Add Redis for queue management
- [ ] Configure SSO with Keycloak
- [ ] Create workflow templates library
- [ ] Implement automated testing for workflows
- [ ] Add workflow version control integration
- [ ] Set up execution data archival
- [ ] Create custom nodes for internal services
- [ ] Implement workflow approval process
- [ ] Add cost tracking for API calls
