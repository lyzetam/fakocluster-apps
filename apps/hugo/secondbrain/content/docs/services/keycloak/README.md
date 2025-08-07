# Keycloak Identity and Access Management

## Overview

Keycloak is an open-source Identity and Access Management (IAM) solution deployed in the Fako cluster. It provides single sign-on (SSO), user federation, identity brokering, and social login capabilities. This deployment uses Keycloak 26.x with PostgreSQL backend and is configured for high availability with clustering.

## Key Features

- **Single Sign-On (SSO)**: One login for multiple applications
- **Identity Brokering**: Connect to external identity providers
- **User Federation**: Sync users from LDAP or Active Directory
- **Social Login**: Support for Google, GitHub, Facebook, etc.
- **Multi-Factor Authentication**: Enhanced security with MFA
- **High Availability**: Clustered deployment with 2 replicas
- **Secure Credential Management**: Integration with AWS Secrets Manager

## Architecture

### Components

1. **Deployment**: 2-replica deployment with pod anti-affinity
2. **Services**: 
   - Main service on port 8080
   - Headless service for JGroups clustering
3. **Storage**: PostgreSQL database (postgres-cluster)
4. **ConfigMap**: Environment configuration
5. **External Secrets**: 
   - Admin credentials from AWS Secrets Manager
   - Database credentials from AWS Secrets Manager
6. **Init Container**: Database initialization and user setup

### Resource Requirements

- **Memory**: 1Gi (request), 2Gi (limit) per pod
- **CPU**: 500m (request), 1000m (limit) per pod
- **Database**: PostgreSQL with dedicated database and user

## Configuration

### Environment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `KC_HOSTNAME` | `https://auth.landryzetam.net` | External hostname |
| `KC_HOSTNAME_STRICT` | `false` | Allow backend access |
| `KC_HTTP_ENABLED` | `true` | Enable HTTP (behind proxy) |
| `KC_PROXY` | `edge` | Running behind edge proxy |
| `KC_PROXY_HEADERS` | `xforwarded` | Use X-Forwarded headers |
| `KC_HEALTH_ENABLED` | `true` | Enable health endpoints |
| `KC_METRICS_ENABLED` | `true` | Enable metrics |
| `KC_CACHE_STACK` | `kubernetes` | Use Kubernetes discovery |

### Database Configuration

- **Type**: PostgreSQL
- **Host**: `postgres-cluster-rw.postgres.svc.cluster.local`
- **Port**: 5432
- **Database**: `keycloak`
- **Credentials**: Managed via AWS Secrets Manager

### Clustering Configuration

JGroups clustering is configured for session replication:
- **Discovery**: DNS-based using headless service
- **Query**: `keycloak-headless.keycloak.svc.cluster.local`
- **Port**: 7800

## Usage

### Accessing Keycloak

External access:
```
https://auth.landryzetam.net
```

Internal access:
```
http://keycloak.keycloak.svc.cluster.local:8080
```

### Admin Console

1. Navigate to `https://auth.landryzetam.net/admin`
2. Login with admin credentials from AWS Secrets Manager

### Creating a Realm

1. Login to admin console
2. Click on the realm dropdown (top-left)
3. Click "Create Realm"
4. Configure realm settings:
   - Name
   - Display name
   - Login settings
   - Token settings

### Adding Applications

```bash
# Example: Register an application
1. Select your realm
2. Navigate to Clients → Create
3. Configure:
   - Client ID: your-app-id
   - Client Protocol: openid-connect
   - Root URL: https://your-app.example.com
```

### User Management

#### Create User
```bash
# Via Admin Console
1. Select realm
2. Navigate to Users → Add user
3. Fill in user details
4. Set temporary password
```

#### Import Users from LDAP
```bash
# Configure User Federation
1. Navigate to User Federation
2. Add provider → LDAP
3. Configure connection settings
4. Set up attribute mappings
```

## Operations

### Checking Service Status

```bash
# Check pods
kubectl get pods -n keycloak

# View logs
kubectl logs -n keycloak -l app=keycloak

# Check cluster status
kubectl exec -n keycloak deployment/keycloak -- \
  curl -s http://localhost:9000/health/ready
```

### Database Management

#### Check Database Connection
```bash
kubectl exec -n keycloak deployment/keycloak -- \
  env | grep KC_DB
```

#### Database Maintenance
```bash
# Connect to PostgreSQL
kubectl exec -it -n postgres postgres-cluster-rw-0 -- psql -U postgres -d keycloak

# Check Keycloak tables
\dt realm*
```

### Backup and Restore

#### Export Realm
```bash
# Export specific realm
kubectl exec -n keycloak deployment/keycloak -- \
  /opt/keycloak/bin/kc.sh export \
  --file /tmp/realm-export.json \
  --realm your-realm

# Copy export locally
kubectl cp keycloak/keycloak-pod:/tmp/realm-export.json ./realm-backup.json
```

#### Import Realm
```bash
# Copy file to pod
kubectl cp ./realm-backup.json keycloak/keycloak-pod:/tmp/realm-import.json

# Import realm
kubectl exec -n keycloak deployment/keycloak -- \
  /opt/keycloak/bin/kc.sh import \
  --file /tmp/realm-import.json
```

## Troubleshooting

### Pod Not Starting

1. **Check init container logs**:
```bash
kubectl logs -n keycloak -l app=keycloak -c database-init
```

2. **Verify AWS credentials**:
```bash
kubectl get secret -n keycloak aws-credentials-env
```

3. **Check external secrets**:
```bash
kubectl get externalsecret -n keycloak
kubectl describe externalsecret -n keycloak keycloak-admin-credentials
```

### Authentication Issues

1. **Check admin credentials**:
```bash
kubectl get secret -n keycloak keycloak-admin-credentials -o yaml
```

2. **Reset admin password**:
```bash
# Connect to pod
kubectl exec -it -n keycloak deployment/keycloak -- bash

# Reset password
/opt/keycloak/bin/kc.sh start-dev \
  --bootstrap-admin-username=admin \
  --bootstrap-admin-password=newpassword
```

### Clustering Issues

1. **Check JGroups discovery**:
```bash
# View cluster members
kubectl exec -n keycloak deployment/keycloak -- \
  nslookup keycloak-headless.keycloak.svc.cluster.local
```

2. **Check JGroups logs**:
```bash
kubectl logs -n keycloak -l app=keycloak | grep -i jgroups
```

### Performance Issues

1. **Monitor resource usage**:
```bash
kubectl top pods -n keycloak
```

2. **Check database performance**:
```bash
# Long-running queries
kubectl exec -n postgres postgres-cluster-rw-0 -- \
  psql -U postgres -d keycloak -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"
```

## Security Considerations

### Credential Management
- Admin credentials stored in AWS Secrets Manager
- Database credentials managed via External Secrets Operator
- No hardcoded passwords in configurations

### Network Security
- TLS termination at ingress
- Internal communication over HTTP (secure network)
- Consider implementing network policies

### Best Practices
1. **Regular Updates**: Keep Keycloak version updated
2. **Audit Logging**: Enable and monitor audit logs
3. **Token Rotation**: Configure appropriate token lifetimes
4. **Password Policies**: Enforce strong password requirements
5. **MFA**: Enable multi-factor authentication for admin accounts

## Integration Examples

### OAuth2/OIDC Client Configuration

#### Spring Boot Application
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            client-id: your-app
            client-secret: ${CLIENT_SECRET}
            scope: openid,profile,email
            authorization-grant-type: authorization_code
        provider:
          keycloak:
            issuer-uri: https://auth.landryzetam.net/realms/your-realm
```

#### Node.js Application
```javascript
const Keycloak = require('keycloak-connect');

const keycloak = new Keycloak({
  realm: 'your-realm',
  'auth-server-url': 'https://auth.landryzetam.net/',
  'ssl-required': 'external',
  clientId: 'your-app',
  credentials: {
    secret: process.env.CLIENT_SECRET
  }
});
```

### Service Account Setup

```bash
# Create service account
1. Create client with:
   - Access Type: confidential
   - Service Accounts Enabled: true
2. Note the client secret
3. Assign roles to service account
```

## Monitoring

### Key Metrics
- Login success/failure rates
- Token issuance rate
- Database connection pool usage
- Memory and CPU utilization
- Response times

### Health Endpoints
- **Readiness**: `http://keycloak:9000/health/ready`
- **Liveness**: `http://keycloak:9000/health/live`
- **Metrics**: `http://keycloak:9000/metrics`

### Prometheus Integration
```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: keycloak
  namespace: keycloak
spec:
  selector:
    matchLabels:
      app: keycloak
  endpoints:
  - port: management
    path: /metrics
```

## Maintenance

### Version Upgrades

1. **Backup current state**:
   - Export all realms
   - Backup database

2. **Test upgrade**:
   - Deploy new version in staging
   - Verify functionality

3. **Rolling upgrade**:
   - Update image version
   - Monitor pod rollout

### Database Maintenance

```bash
# Vacuum database
kubectl exec -n postgres postgres-cluster-rw-0 -- \
  psql -U postgres -d keycloak -c "VACUUM ANALYZE;"

# Check table sizes
kubectl exec -n postgres postgres-cluster-rw-0 -- \
  psql -U postgres -d keycloak -c \
  "SELECT schemaname,tablename,pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables WHERE schemaname='public' ORDER BY pg_relation_size(schemaname||'.'||tablename) DESC;"
```

## Future Improvements

- [ ] Implement automated backup strategy
- [ ] Add Grafana dashboards for monitoring
- [ ] Configure audit logging to external system
- [ ] Implement custom themes
- [ ] Add support for WebAuthn/FIDO2
- [ ] Configure user self-registration workflows
- [ ] Implement automated realm provisioning
- [ ] Add integration with external identity providers
