"""Configuration for Oura Health Dashboard - Kubernetes optimized"""
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database Configuration - From K8s secrets
DATABASE_HOST = os.environ.get('DATABASE_HOST', 'localhost')
DATABASE_PORT = int(os.environ.get('DATABASE_PORT', '5432'))
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'oura_health')
DATABASE_USER = os.environ.get('DATABASE_USER', 'postgres')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'password')

# Build connection string
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f'postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
)

# Log database connection info (without password)
logger.info(f"Database configured: {DATABASE_USER}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")

# Streamlit Configuration
STREAMLIT_PORT = int(os.environ.get('STREAMLIT_SERVER_PORT', '8501'))
STREAMLIT_SERVER_ADDRESS = os.environ.get('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')

# Dashboard Settings - From K8s ConfigMap
DEFAULT_DATE_RANGE_DAYS = int(os.environ.get('DEFAULT_DATE_RANGE_DAYS', '30'))
ENABLE_CACHING = os.environ.get('ENABLE_CACHING', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '3600'))  # 1 hour

# Chart Theme
CHART_THEME = os.environ.get('CHART_THEME', 'plotly')  # or 'plotly_dark', 'plotly_white'

# Feature Flags - From K8s ConfigMap
ENABLE_EXPORT = os.environ.get('ENABLE_EXPORT', 'true').lower() == 'true'
ENABLE_COMPARISONS = os.environ.get('ENABLE_COMPARISONS', 'true').lower() == 'true'
ENABLE_PREDICTIONS = os.environ.get('ENABLE_PREDICTIONS', 'false').lower() == 'true'

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Performance settings for K8s
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))
CONNECTION_POOL_SIZE = int(os.environ.get('CONNECTION_POOL_SIZE', '5'))
CONNECTION_POOL_OVERFLOW = int(os.environ.get('CONNECTION_POOL_OVERFLOW', '10'))

# Security settings
REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', '60'))

# Validate configuration
def validate_config():
    """Validate that required configuration is present"""
    errors = []
    
    if not DATABASE_HOST:
        errors.append("DATABASE_HOST is not set")
    if not DATABASE_USER:
        errors.append("DATABASE_USER is not set")
    if not DATABASE_PASSWORD:
        errors.append("DATABASE_PASSWORD is not set")
    if not DATABASE_NAME:
        errors.append("DATABASE_NAME is not set")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    logger.info("Configuration validated successfully")

# Validate on import
try:
    validate_config()
except ValueError as e:
    logger.warning(f"Configuration validation failed: {e}")
    # Don't fail immediately in case we're running locally