# pgAdmin PostgreSQL Management Tool

## Overview

pgAdmin is a comprehensive web-based management tool for PostgreSQL deployed in the Fako cluster. It provides a graphical interface for database administration, query execution, and monitoring. This deployment is pre-configured to connect to the PostgreSQL cluster with both read-write and read-only endpoints, making database management accessible through a web browser.

## Key Features

- **Web-Based Interface**: Full-featured PostgreSQL management from browser
- **Pre-Configured Servers**: Automatic connection to cluster databases
- **Query Tool**: Advanced SQL editor with syntax highlighting
- **Visual Database Designer**: ERD and schema visualization
- **Backup/Restore**: GUI for database backup operations
- **Server Monitoring**: Real-time database statistics
- **User Management**: Graphical user and role administration

## Architecture

### Components

1. **Deployment**: Single-replica deployment
2. **Service**: ClusterIP service on port 80
3. **Ingress**: HTTPS access (when configured)
4. **Storage**: PersistentVolumeClaim for pgAdmin data
5. **ConfigMap**: Server configuration and connection settings
6. **External Secrets**: Database passwords from AWS Secrets Manager

### Resource Requirements

- **Memory**: 256Mi (request), 512Mi (limit)
- **CPU**: 250m (request), 500m (limit)
- **Storage**: Persistent volume for pgAdmin data and sessions

## Configuration

### Environment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `PGADMIN_DEFAULT_EMAIL` | `85landry@gmail.com` | Admin login email |
| `PGADMIN_CONFIG_SERVER_MODE` | `False` | Desktop mode (single user) |
| `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED` | `False` | No master password needed |
| `PGADMIN_SERVER_JSON_FILE` | `/pgadmin4/servers.json` | Pre-configured servers |

### Pre-Configured Database Servers

1. **PostgreSQL Cluster (Read-Write)**
   - Host: `postgres-cluster-rw.postgres.svc.cluster.local`
   - Port: 5432
   - Database: `app`
   - User: `app`

2. **PostgreSQL Cluster (Read-Only)**
   - Host: `postgres-cluster-ro.postgres.svc.cluster.local`
   - Port: 5432
   - Database: `app`
   - User: `app`

## Usage

### Accessing pgAdmin

External access (requires ingress):
```
https://pgadmin.your-domain.com
```

Internal access:
```
http://pgadmin.pgadmin.svc.cluster.local
```

Port forwarding for local access:
```bash
kubectl port-forward -n pgadmin svc/pgadmin 8080:80
# Access at http://localhost:8080
```

### Initial Login

1. Navigate to pgAdmin URL
2. Login with:
   - Email: `85landry@gmail.com`
   - Password: From `pgadmin-secret`

### Common Tasks

#### Connect to Database
1. Servers are pre-configured
2. Click on "PostgreSQL Cluster" in left panel
3. Enter password when prompted
4. Browse databases, schemas, tables

#### Execute Queries
1. Right-click on database
2. Select "Query Tool"
3. Write and execute SQL
4. View results in grid or chart

#### Create Database Backup
1. Right-click on database
2. Select "Backup..."
3. Configure backup options
4. Save to pgAdmin storage

#### Monitor Database Activity
1. Select server in tree
2. Click "Dashboard" tab
3. View real-time metrics:
   - Active connections
   - Transaction rates
   - Database sizes
   - Query performance

## Operations

### Checking Service Status

```bash
# Check pod status
kubectl get pods -n pgadmin

# View logs
kubectl logs -n pgadmin deployment/pgadmin

# Check storage usage
kubectl exec -n pgadmin deployment/pgadmin -- df -h /var/lib/pgadmin
```

### Managing Server Connections

#### Add New Server
1. Right-click "Servers" → "Create" → "Server"
2. Configure connection details
3. Save password (optional)

#### Export Server List
```bash
# Get current server configuration
kubectl exec -n pgadmin deployment/pgadmin -- \
  cat /var/lib/pgadmin/pgadmin4.db
```

### Password Management

Passwords are stored via:
- `.pgpass` file for automatic authentication
- External Secrets from AWS Secrets Manager
- pgAdmin's internal password storage

## Troubleshooting

### Cannot Login

1. **Check secret**:
```bash
kubectl get secret pgadmin-secret -n pgadmin -o yaml
```

2. **Reset admin password**:
```bash
kubectl exec -it -n pgadmin deployment/pgadmin -- \
  python /pgadmin4/setup.py --email 85landry@gmail.com --password NewPassword
```

### Connection Failed to Database

1. **Test connectivity**:
```bash
kubectl exec -n pgadmin deployment/pgadmin -- \
  nc -zv postgres-cluster-rw.postgres.svc.cluster.local 5432
```

2. **Check pgpass file**:
```bash
kubectl exec -n pgadmin deployment/pgadmin -- cat /var/lib/pgadmin/.pgpass
```

3. **Verify credentials**:
```bash
kubectl get secret -n pgadmin pgadmin-pgpass -o yaml
```

### Performance Issues

1. **Check resource usage**:
```bash
kubectl top pod -n pgadmin
```

2. **Clear query history**:
   - Settings → Clear Query History
   - Remove old backup files

3. **Restart pod**:
```bash
kubectl rollout restart deployment/pgadmin -n pgadmin
```

### Storage Full

1. **Check usage**:
```bash
kubectl exec -n pgadmin deployment/pgadmin -- \
  du -sh /var/lib/pgadmin/*
```

2. **Clean up**:
   - Remove old backups
   - Clear session data
   - Delete query history

## Security Considerations

### Authentication
- Default setup uses single admin account
- Consider implementing:
  - LDAP/AD integration
  - OAuth with Keycloak
  - Multi-user mode

### Network Security
- No TLS by default (use ingress)
- Implement network policies
- Restrict database access

### Best Practices
1. **Change default email**: Update admin email
2. **Strong passwords**: Use complex passwords
3. **Regular updates**: Keep pgAdmin updated
4. **Audit logs**: Enable and monitor logs
5. **Backup pgAdmin data**: Include in backup strategy

## Advanced Configuration

### Enable Multi-User Mode

```yaml
# In configmap
PGADMIN_CONFIG_SERVER_MODE: "True"
PGADMIN_CONFIG_MAIL_SERVER: "smtp.example.com"
PGADMIN_CONFIG_MAIL_PORT: "587"
```

### Add SSL/TLS

```yaml
# In deployment
env:
- name: PGADMIN_ENABLE_TLS
  value: "True"
volumeMounts:
- name: certs
  mountPath: /certs
```

### Configure External Authentication

```yaml
# OAuth2 with Keycloak
PGADMIN_CONFIG_AUTHENTICATION_SOURCES: ["oauth2"]
PGADMIN_CONFIG_OAUTH2_CLIENT_ID: "pgadmin"
PGADMIN_CONFIG_OAUTH2_CLIENT_SECRET: "${CLIENT_SECRET}"
PGADMIN_CONFIG_OAUTH2_TOKEN_URL: "https://auth.landryzetam.net/realms/master/protocol/openid-connect/token"
```

## Monitoring

### Key Metrics
- Login success/failure rates
- Query execution times
- Active user sessions
- Storage usage
- Memory consumption

### Health Checks

Add health check endpoint:
```yaml
livenessProbe:
  httpGet:
    path: /misc/ping
    port: 80
  initialDelaySeconds: 30
  periodSeconds: 10
```

## Integration Examples

### With Grafana

Create PostgreSQL datasource:
1. Use connection details from pgAdmin
2. Configure in Grafana
3. Build dashboards

### With Backup Tools

Configure pgAdmin for automated backups:
```python
# Backup script
import subprocess

subprocess.run([
    "pg_dump",
    "-h", "postgres-cluster-rw.postgres.svc.cluster.local",
    "-U", "app",
    "-d", "mydb",
    "-f", "/backups/mydb.sql"
])
```

### With CI/CD

Use pgAdmin for database migrations:
1. Store migration scripts
2. Execute via Query Tool
3. Track schema versions

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor active connections
   - Check for failed queries

2. **Weekly**:
   - Review storage usage
   - Clean old session data
   - Check for updates

3. **Monthly**:
   - Audit user access
   - Review server configurations
   - Update pgAdmin version

### Upgrade Procedure

1. **Backup pgAdmin data**:
```bash
kubectl exec -n pgadmin deployment/pgadmin -- \
  tar -czf /tmp/pgadmin-backup.tar.gz /var/lib/pgadmin
```

2. **Update image**:
```yaml
image: dpage/pgadmin4:9.7.0
```

3. **Verify functionality**:
   - Test login
   - Check server connections
   - Verify saved queries

## Performance Optimization

### Query Performance
- Use EXPLAIN ANALYZE
- Create appropriate indexes
- Monitor slow queries
- Optimize query plans

### pgAdmin Performance
- Limit query result size
- Use pagination
- Clear old data regularly
- Increase resources if needed

### Database Connection
- Use connection pooling
- Set appropriate timeouts
- Monitor connection count
- Close idle connections

## Future Improvements

- [ ] Implement SSO with Keycloak
- [ ] Add automated backup scheduling
- [ ] Create custom dashboards
- [ ] Implement query approval workflow
- [ ] Add database migration tracking
- [ ] Configure email notifications
- [ ] Create user access reports
- [ ] Add query performance analytics
- [ ] Implement schema version control
- [ ] Add cost tracking for queries
