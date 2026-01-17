"""Configuration for Oura data collector with PostgreSQL support"""
import os

# AWS Configuration
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
OURA_SECRETS_NAME = os.environ.get('OURA_SECRETS_NAME', 'oura/api-credentials')
POSTGRES_SECRETS_NAME = os.environ.get('POSTGRES_SECRETS_NAME', 'postgres/app-user')

# Storage Configuration
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'postgres')  # 'postgres' or 'file'
DATA_DIR = os.environ.get('DATA_DIR', '/data')  # Only used if STORAGE_BACKEND is 'file'
OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # Only used if STORAGE_BACKEND is 'file'

# PostgreSQL Configuration (will be loaded from AWS Secrets Manager)
DATABASE_HOST = os.environ.get('DATABASE_HOST', None)
DATABASE_PORT = os.environ.get('DATABASE_PORT', '5432')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'oura_health')

# Collection Configuration
COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', '3600'))  # 1 hour
DAYS_TO_BACKFILL = int(os.environ.get('DAYS_TO_BACKFILL', '7'))
RUN_ONCE = os.environ.get('RUN_ONCE', 'false').lower() == 'true'

# Oura API Configuration
OURA_API_BASE_URL = 'https://api.ouraring.com/v2'
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Stale Data Detection
STALE_DATA_THRESHOLD_DAYS = int(os.environ.get('STALE_DATA_THRESHOLD_DAYS', '3'))
ALERT_ON_STALE_DATA = os.environ.get('ALERT_ON_STALE_DATA', 'true').lower() == 'true'
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')

# Critical tables that should have recent data (detailed data from ring sync)
CRITICAL_TABLES = ['sleep_periods', 'activity']
# Score tables that may have data even without ring sync
SCORE_TABLES = ['daily_sleep', 'readiness']