# Katikaa Health Monitor

A comprehensive health monitoring dashboard for the Katikaa prediction platform that provides real-time insights into financial health, user engagement, payment gateway status, and system performance.

## Features

- **Financial Health Monitoring**: Real-time tracking of wallet balances, transaction volumes, and revenue metrics
- **User Engagement Analytics**: Community participation, prediction accuracy, and user growth trends
- **Payment Gateway Health**: Fapshi integration monitoring with success/failure rates
- **API Usage Monitoring**: SportMonks API consumption tracking and threshold alerts
- **System Performance**: Database health, response times, and error rate monitoring
- **Automated Alerting**: Configurable thresholds with email/Slack notifications
- **Health Score Dashboard**: Overall platform health scoring with trend analysis

## Architecture

```
katikaa-health-monitor/
├── app/                    # Main application code
│   ├── main.py            # Streamlit dashboard entry point
│   ├── health_metrics.py  # Core health calculation logic
│   └── components/        # Modular health monitoring components
├── data/                  # Database connections and queries
├── utils/                 # Utilities for charts, reporting, notifications
├── static/               # Static assets
├── templates/            # HTML templates
├── tests/                # Unit tests
└── docs/                 # Documentation
```

## Quick Start

### Using Docker

```bash
# Clone the repository
git clone <repository-url>
cd katikaa-health-monitor

# Build and run with Docker Compose
docker-compose up --build
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials and API keys

# Run the application
streamlit run app/main.py
```

## Environment Variables

```bash
# Database Configuration
DB_HOST=your-database-host
DB_PORT=3306
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password

# External APIs
FAPSHI_PAYMENT_API_USER=your-fapshi-payment-api-user
FAPSHI_PAYMENT_API_KEY=your-fapshi-payment-api-key
FAPSHI_CASHOUT_API_USER=your-fapshi-cashout-api-user
FAPSHI_CASHOUT_API_KEY=your-fapshi-cashout-api-key
SPORTMONKS_API_TOKEN=your-sportmonks-api-token

# AWS Configuration (for secrets management)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Alerting Configuration
SLACK_WEBHOOK_URL=your-slack-webhook-url
NOTIFICATION_EMAIL=alerts@yourcompany.com
```

## Health Metrics

### Financial Health
- Total user funds in FCFA
- Daily transaction volumes
- Failed transaction rates
- Commission tracking
- Revenue trends

### User Engagement
- Daily/Monthly active users
- Community participation rates
- Prediction accuracy scores
- User growth trends

### System Health
- API response times
- Database connection status
- Error rates
- Resource utilization

### Payment Gateway Health
- Fapshi balance monitoring
- Transaction success rates
- Failed payment analysis
- Settlement tracking

## Deployment

### Production Deployment

```bash
# Using Docker Compose for production
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

## API Endpoints

- `/health` - Overall health status
- `/metrics` - Prometheus metrics endpoint
- `/api/financial-health` - Financial health data
- `/api/user-engagement` - User engagement metrics
- `/api/payment-health` - Payment gateway status
- `/api/alerts` - Active alerts and notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is proprietary software for Katikaa platform monitoring.

## Support

For support and questions, contact the development team or create an issue in the repository.
