# PostgreSQL Cluster Service

## Overview

The PostgreSQL Cluster is a highly available database service deployed using CloudNative PG (CNPG) operator. It provides a 3-node PostgreSQL 16.2 cluster with automatic failover, backup scheduling, and secure credential management through AWS Secrets Manager. This cluster serves as the primary database backend for multiple services including Keycloak, N8N, and other applications.

## Key Features

- **High Availability**: 3-node cluster with automatic failover
- **Automated Backups**: Daily scheduled backups at 2 AM
- **Secure Credentials**: Integration with AWS Secrets Manager
- **Connection Pooling**: PgBouncer pooler for efficient connections
- **Performance Tuned**: Optimized PostgreSQL parameters
- **Pod Anti-Affinity**: Instances spread across different nodes
- **Monitoring Ready**: Prometheus metrics support

## Architecture

### Components

1. **Cluster**: 3 PostgreSQL instances (1 primary, 2 replicas)
2. **Operator**: CloudNative PG operator manages the cluster
3. **Storage**: 50Gi persistent volume per instance
4. **Pooler**: PgBouncer connection pooler
5. **Backup**: Scheduled backup with retention policy
6. **External Secrets**: AWS Secrets Manager integration

### Resource Requirements

- **Memory**: 2Gi (request), 4Gi (limit) per instance
- **CPU**: 1 core (request), 2 cores (limit) per instance
- **Storage**: 50Gi per instance (150Gi total)
- **Storage Class**: `nfs-postgres-v2`

## Configuration

### PostgreSQL Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_connections` | `200` | Maximum concurrent connections |
| `shared_buffers` | `512MB` | Memory for caching data |
| `effective_cache_size` | `3GB` | Planner's assumption about cache |
| `work_mem` | `8MB` | Memory for query operations |
| `wal_buffers` | `16MB` | WAL write buffer size |
| `maintenance_work_mem` | `64MB` | Memory for maintenance operations |
| `max_wal_size` | `1GB` | Maximum WAL size before checkpoint |
| `checkpoint_timeout` | `5min` | Time between checkpoints |

### Network Access

The cluster allows connections from:
- `10.0.0.0/8` - Kubernetes pod network
- `172.16.0.0/12` - Docker networks
- `192.168.0.0/16` - Local networks

## Usage

### Connection Details

#### Primary (Read/Write)
```
Host: postgres-cluster-rw.postgres.svc.cluster.local
Port: 5432
Database: app (or specify your database)
SSL: Enabled
```

#### Read-Only Replicas
```
Host: postgres-cluster-ro.postgres.svc.cluster.local
Port: 5432
```

#### Any Instance (Load Balanced)
```
Host: postgres-cluster-r.postgres.svc.cluster.local
Port: 5432
```

### Connection Pooler

For applications requiring connection pooling:
```
Host: postgres-cluster-pooler-rw.postgres.svc.cluster.local
Port: 5432
```

### Creating a Database

1. **Connect as superuser**:
```bash
kubectl exec -it -n postgres postgres-cluster-1 -- psql -U postgres
```

2. **Create database and user**:
```sql
CREATE DATABASE myapp;
CREATE USER myapp_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE myapp TO myapp_user;
```

### Using AWS Secrets Manager

Credentials are stored in AWS Secrets Manager:
- **Admin credentials**: `postgres/admin-credentials`
- **App user credentials**: `postgres/app-credentials`

Format:
```json
{
  "username": "postgres",
  "password": "secure_password"
}
```

## Operations

### Checking Cluster Status

```bash
# Check cluster status
kubectl get cluster -n postgres

# Detailed cluster information
kubectl describe cluster postgres-cluster -n postgres

# Check pod status
kubectl get pods -n postgres -l postgresql=postgres-cluster

# View cluster events
kubectl get events -n postgres --field-selector involvedObject.name=postgres-cluster
```

### Monitoring Replication

```bash
# Check replication status
kubectl exec -n postgres postgres-cluster-1 -- psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Check replication lag
kubectl exec -n postgres postgres-cluster-2 -- psql -U postgres -c "SELECT pg_last_wal_receive_lsn() - pg_last_wal_replay_lsn() AS lag;"
```

### Manual Failover

```bash
# Promote a specific instance to primary
kubectl cnpg promote postgres-cluster-2 -n postgres
```

### Backup Management

#### List Backups
```bash
kubectl get backups -n postgres
```

#### Trigger Manual Backup
```bash
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: postgres-cluster-manual-$(date +%Y%m%d%H%M%S)
  namespace: postgres
spec:
  cluster:
    name: postgres-cluster
EOF
```

#### Restore from Backup
```bash
# Create a new cluster from backup
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster-restored
  namespace: postgres
spec:
  # ... other specs ...
  bootstrap:
    recovery:
      backup:
        name: <backup-name>
EOF
```

## Troubleshooting

### Cluster Not Starting

1. **Check operator logs**:
```bash
kubectl logs -n cnpg-system deployment/cnpg-controller-manager
```

2. **Check instance logs**:
```bash
kubectl logs -n postgres postgres-cluster-1
```

3. **Verify secrets**:
```bash
kubectl get secrets -n postgres
kubectl describe externalsecret -n postgres
```

### Connection Issues

1. **Test connectivity**:
```bash
kubectl run -it --rm psql-test --image=postgres:16 --restart=Never -- \
  psql -h postgres-cluster-rw.postgres.svc.cluster.local -U postgres -d postgres
```

2. **Check service endpoints**:
```bash
kubectl get endpoints -n postgres
```

3. **Verify network policies**:
```bash
kubectl get networkpolicies -n postgres
```

### Performance Issues

1. **Check resource usage**:
```bash
kubectl top pods -n postgres
```

2. **View slow queries**:
```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

3. **Check connection count**:
```sql
SELECT count(*) FROM pg_stat_activity;
```

### Storage Issues

1. **Check PVC status**:
```bash
kubectl get pvc -n postgres
```

2. **Monitor disk usage**:
```bash
kubectl exec -n postgres postgres-cluster-1 -- df -h /var/lib/postgresql/data
```

## Performance Tuning

### Query Optimization

1. **Enable query statistics**:
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

2. **Analyze tables regularly**:
```sql
ANALYZE;
```

3. **Monitor index usage**:
```sql
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

### Connection Pool Tuning

Edit pooler configuration:
```yaml
# In pooler.yaml
spec:
  instances: 3
  pgbouncer:
    poolMode: transaction
    parameters:
      max_client_conn: "1000"
      default_pool_size: "25"
```

### Resource Optimization

For write-heavy workloads:
```yaml
postgresql:
  parameters:
    wal_buffers: "32MB"
    checkpoint_segments: "32"
    checkpoint_completion_target: "0.9"
```

## Security Considerations

### Authentication
- Superuser credentials in AWS Secrets Manager
- MD5 authentication for network connections
- SSL/TLS enabled by default

### Network Security
- Pod-to-pod communication only
- Network policies recommended
- No external exposure by default

### Backup Security
- Backups inherit cluster RBAC
- Consider encryption at rest
- Regular backup testing recommended

### Best Practices
1. **Regular password rotation**
2. **Audit logging enabled**
3. **Principle of least privilege**
4. **Connection limits per user**
5. **Regular security updates**

## Monitoring

### Key Metrics
- Replication lag
- Connection pool saturation
- Query response times
- Disk I/O and space usage
- CPU and memory utilization
- Transaction rate
- Cache hit ratio

### Prometheus Queries

```promql
# Replication lag
pg_replication_lag_seconds

# Active connections
pg_stat_activity_count

# Database size
pg_database_size_bytes

# Transaction rate
rate(pg_stat_database_xact_commit[5m])
```

### Grafana Dashboard

Import dashboard ID: 9628 (PostgreSQL Database)

## Maintenance

### Regular Tasks

1. **Weekly**: 
   - Check backup completion
   - Review slow query log
   - Analyze tables

2. **Monthly**:
   - Review connection pool settings
   - Check index usage
   - Update statistics

3. **Quarterly**:
   - PostgreSQL version updates
   - Security audit
   - Performance baseline review

### Upgrade Procedure

1. **Test in staging**
2. **Backup production**
3. **Update image version**:
```yaml
spec:
  imageName: ghcr.io/cloudnative-pg/postgresql:16.3
```
4. **Monitor rolling update**

## Integration Examples

### Application Connection String

```python
# Python with psycopg2
import psycopg2

conn = psycopg2.connect(
    host="postgres-cluster-pooler-rw.postgres.svc.cluster.local",
    database="myapp",
    user="myapp_user",
    password="from_secret"
)
```

### Spring Boot Configuration

```yaml
spring:
  datasource:
    url: jdbc:postgresql://postgres-cluster-pooler-rw.postgres.svc.cluster.local:5432/myapp
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 10
```

## Future Improvements

- [ ] Implement automated backup testing
- [ ] Add pgAudit for compliance logging
- [ ] Configure streaming replication to DR site
- [ ] Implement automatic VACUUM scheduling
- [ ] Add TimescaleDB extension for time-series data
- [ ] Create backup retention lifecycle policies
- [ ] Implement connection pool per application
- [ ] Add read replica auto-scaling
