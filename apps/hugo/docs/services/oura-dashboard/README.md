# Oura Dashboard - Health Data Visualization Platform

## Overview

Oura Dashboard is a Streamlit-based web application deployed in the Fako cluster that provides interactive visualization of health data collected from the Oura Ring. It connects to the PostgreSQL database populated by the Oura Collector service and presents comprehensive health insights through charts, graphs, and analytics. The dashboard is secured with OAuth2 authentication and provides personalized health tracking capabilities for sleep, activity, readiness, and heart rate metrics.

## Key Features

- **Interactive Visualizations**: Real-time charts and graphs using Streamlit
- **Comprehensive Metrics**: Sleep, activity, readiness, and HRV analytics
- **OAuth2 Authentication**: Secure access with OAuth2 proxy
- **PostgreSQL Integration**: Direct database queries for data
- **Responsive Design**: Mobile-friendly interface
- **Health Trends**: Long-term pattern analysis
- **Custom Reports**: Exportable health summaries
- **Real-time Updates**: Auto-refresh capabilities

## Architecture

### Components

1. **Streamlit App**: Python-based web dashboard
2. **OAuth2 Proxy**: Authentication layer
3. **Service**: ClusterIP on port 8501
4. **Ingress**: HTTPS access with authentication
5. **External Secrets**: AWS Secrets Manager integration
6. **Database Connection**: PostgreSQL read access

### Resource Requirements

- **Memory**: 256Mi (request), 512Mi (limit)
- **CPU**: 100m (request), 500m (limit)
- **Storage**: EmptyDir for temporary data
- **Port**: 8501 (Streamlit default)

## Configuration

### Environment Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DATABASE_NAME` | `app` | PostgreSQL database |
| `DAYS_TO_BACKFILL` | `7` | Default data range |
| `LOG_LEVEL` | `INFO` | Application logging |
| `API_TIMEOUT` | `30` | Query timeout |

### OAuth2 Configuration

Protected by OAuth2 proxy for secure access:
- Provider: Configured in external secret
- Cookie secret: Auto-generated
- Email domain restrictions

## Usage

### Accessing the Dashboard

External access (with authentication):
```
https://oura-dashboard.your-domain.com
```

Internal access (port forward):
```bash
kubectl port-forward -n oura-dashboard svc/oura-dashboard 8501:8501
# Access at http://localhost:8501
```

### Dashboard Features

1. **Overview Page**:
   - Daily health summary
   - Key metrics at a glance
   - Recent trends

2. **Sleep Analysis**:
   - Sleep stages breakdown
   - Sleep quality trends
   - Bedtime consistency
   - REM/Deep sleep patterns

3. **Activity Tracking**:
   - Daily steps and calories
   - Activity intensity
   - Movement patterns
   - Goal achievement

4. **Readiness Insights**:
   - HRV trends
   - Recovery status
   - Temperature deviation
   - Readiness contributors

5. **Reports**:
   - Weekly/monthly summaries
   - Exportable data
   - Custom date ranges

## Operations

### Health Monitoring

```bash
# Check dashboard health
kubectl get pods -n oura-dashboard

# View logs
kubectl logs -n oura-dashboard -l app=oura-dashboard

# Check OAuth2 proxy
kubectl logs -n oura-dashboard -l app=oauth2-proxy
```

### Database Queries

The dashboard executes various queries:
```sql
-- Example: Weekly sleep average
SELECT 
  DATE_TRUNC('week', date) as week,
  AVG(total_sleep) as avg_sleep,
  AVG(deep_sleep) as avg_deep,
  AVG(rem_sleep) as avg_rem
FROM oura_sleep
WHERE date > CURRENT_DATE - INTERVAL '30 days'
GROUP BY week;
```

### Performance Optimization

1. **Query caching**:
   - Implements session-based caching
   - Reduces database load

2. **Data aggregation**:
   - Pre-computed daily summaries
   - Efficient time-series queries

## Troubleshooting

### Dashboard Not Loading

1. **Check Streamlit health**:
```bash
kubectl exec -n oura-dashboard deployment/oura-dashboard -- \
  curl -s http://localhost:8501/_stcore/health
```

2. **Verify database connection**:
```bash
kubectl exec -n oura-dashboard deployment/oura-dashboard -- \
  pg_isready -h postgres-cluster-rw.postgres.svc.cluster.local
```

### Authentication Issues

1. **Check OAuth2 proxy**:
```bash
kubectl logs -n oura-dashboard deployment/oauth2-proxy
```

2. **Verify cookie secret**:
```bash
kubectl get secret oauth2-proxy -n oura-dashboard
```

### Data Not Displaying

1. **Check data availability**:
```bash
# Connect to database
kubectl exec -it -n postgres postgres-cluster-1 -- \
  psql -U app -c "SELECT COUNT(*) FROM oura_sleep;"
```

2. **Verify permissions**:
```bash
kubectl describe externalsecret -n oura-dashboard
```

## Security Considerations

### Authentication
- OAuth2 proxy for external access
- Cookie-based sessions
- Email domain restrictions
- Secure cookie settings

### Database Access
- Read-only database user
- Credentials from AWS Secrets
- SSL connection enforced
- Query timeout limits

### Best Practices
1. **Regular auth audits**: Review access logs
2. **Session management**: Configure timeout
3. **Data privacy**: No PII in logs
4. **HTTPS only**: Enforce encryption
5. **CORS settings**: Restrict origins

## Customization

### Adding New Visualizations

Create custom pages:
```python
# pages/custom_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px

def load_custom_data():
    # Custom query logic
    pass

st.title("Custom Health Analysis")
data = load_custom_data()
fig = px.line(data, x='date', y='metric')
st.plotly_chart(fig)
```

### Theming

Configure Streamlit theme:
```toml
# .streamlit/config.toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### Custom Metrics

Add calculated metrics:
```python
# Sleep debt calculation
def calculate_sleep_debt(df):
    target_sleep = 8 * 60  # 8 hours in minutes
    df['sleep_debt'] = target_sleep - df['total_sleep']
    return df['sleep_debt'].rolling(7).mean()
```

## Monitoring

### Key Metrics
- Page load times
- Query execution duration
- Active user sessions
- Error rates
- Cache hit ratios

### Prometheus Metrics

If enabled:
```yaml
# ServiceMonitor configuration
- job_name: 'oura-dashboard'
  metrics_path: '/metrics'
  static_configs:
    - targets: ['oura-dashboard:9090']
```

### Performance Monitoring

Track slow queries:
```python
import time
import logging

def timed_query(query):
    start = time.time()
    result = execute_query(query)
    duration = time.time() - start
    if duration > 1.0:
        logging.warning(f"Slow query: {duration:.2f}s")
    return result
```

## Maintenance

### Regular Tasks

1. **Daily**:
   - Monitor dashboard availability
   - Check error logs
   - Verify data freshness

2. **Weekly**:
   - Review usage patterns
   - Clean temporary files
   - Update visualizations

3. **Monthly**:
   - Update dashboard image
   - Review OAuth2 settings
   - Performance analysis

### Cache Management

Clear Streamlit cache:
```bash
kubectl exec -n oura-dashboard deployment/oura-dashboard -- \
  rm -rf /data/.streamlit/cache
```

### Session Cleanup

Remove old sessions:
```bash
kubectl exec -n oura-dashboard deployment/oura-dashboard -- \
  find /data/sessions -mtime +7 -delete
```

## Advanced Features

### Real-time Updates

Enable auto-refresh:
```python
# Auto-refresh every 5 minutes
import streamlit as st
import time

if st.checkbox("Auto-refresh"):
    time.sleep(300)
    st.experimental_rerun()
```

### Export Functionality

Add data export:
```python
# Export to CSV
def export_data(df, filename):
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
```

### Comparative Analysis

Compare periods:
```python
# Compare this week vs last week
def compare_weeks(current, previous):
    comparison = {
        'sleep': (current['sleep'].mean() - previous['sleep'].mean()),
        'steps': (current['steps'].mean() - previous['steps'].mean()),
        'readiness': (current['readiness'].mean() - previous['readiness'].mean())
    }
    return comparison
```

## Integration Examples

### With Grafana

Alternative visualization:
```yaml
# Grafana dashboard
{
  "dashboard": {
    "title": "Oura Health Metrics",
    "panels": [{
      "datasource": "PostgreSQL",
      "targets": [{
        "rawSql": "SELECT * FROM oura_sleep"
      }]
    }]
  }
}
```

### With Jupyter

Advanced analysis:
```python
# Jupyter notebook integration
from oura_dashboard import data_loader
import matplotlib.pyplot as plt

df = data_loader.get_sleep_data()
df.plot(x='date', y=['deep_sleep', 'rem_sleep'])
plt.show()
```

### API Endpoints

Add REST API:
```python
# api.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/sleep/{date}")
def get_sleep_data(date: str):
    return query_sleep_data(date)
```

## Future Improvements

- [ ] Add machine learning predictions
- [ ] Implement goal setting features
- [ ] Create mobile app companion
- [ ] Add social sharing capabilities
- [ ] Implement data correlations
- [ ] Add weather impact analysis
- [ ] Create personalized recommendations
- [ ] Add voice interface
- [ ] Implement notifications system
- [ ] Create API for external integrations
