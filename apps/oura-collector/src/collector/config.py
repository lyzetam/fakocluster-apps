# # AWS Configuration
# AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
# SECRETS_NAME = os.environ.get('OURA_SECRETS_NAME', 'oura-health/collector')

# # Collection Configuration
# COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', '3600'))  # 1 hour
# DAYS_TO_BACKFILL = int(os.environ.get('DAYS_TO_BACKFILL', '7'))
# RUN_ONCE = os.environ.get('RUN_ONCE', 'false').lower() == 'true'

# # Storage Configuration
# DATA_DIR = os.environ.get('DATA_DIR', '/data')
# OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # json or csv

# # Oura API Configuration
# OURA_API_BASE_URL = 'https://api.ouraring.com/v2'
# API_TIMEOUT = 30
# MAX_RETRIES = 3
# RETRY_DELAY = 5

# # Logging Configuration
# LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


"""Configuration for Oura data collector"""
import os

# AWS Configuration
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
SECRETS_NAME = os.environ.get('OURA_SECRETS_NAME', 'oura-health/collector')

# Collection Configuration
COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', '3600'))  # 1 hour
DAYS_TO_BACKFILL = int(os.environ.get('DAYS_TO_BACKFILL', '7'))
RUN_ONCE = os.environ.get('RUN_ONCE', 'false').lower() == 'true'

# Storage Configuration
DATA_DIR = os.environ.get('DATA_DIR', '/data')
OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # json or csv

# Oura API Configuration
OURA_API_BASE_URL = 'https://api.ouraring.com/v2'
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
