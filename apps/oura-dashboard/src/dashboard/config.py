"""Configuration for Oura Health Dashboard with AWS Secrets Manager support"""
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
POSTGRES_SECRETS_NAME = os.environ.get('POSTGRES_SECRETS_NAME', 'postgres/app-user')

# Storage Backend Configuration
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'postgres')

# Database Configuration (can be overridden by environment variables)
DATABASE_HOST = os.environ.get('DATABASE_HOST', None)
DATABASE_PORT = os.environ.get('DATABASE_PORT', '5432')
DATABASE_NAME = os.environ.get('DATABASE_NAME', None)
DATABASE_USER = os.environ.get('DATABASE_USER', None)
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', None)

# Fallback connection string if not using AWS Secrets Manager
DATABASE_URL = os.environ.get('DATABASE_URL', None)

# Streamlit Configuration
STREAMLIT_PORT = int(os.environ.get('STREAMLIT_SERVER_PORT', '8501'))
STREAMLIT_SERVER_ADDRESS = os.environ.get('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')

# Dashboard Settings
DEFAULT_DATE_RANGE_DAYS = int(os.environ.get('DEFAULT_DATE_RANGE_DAYS', '30'))
ENABLE_CACHING = os.environ.get('ENABLE_CACHING', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '3600'))  # 1 hour

# Chart Theme
CHART_THEME = os.environ.get('CHART_THEME', 'plotly')  # or 'plotly_dark', 'plotly_white'

# Feature Flags
ENABLE_EXPORT = os.environ.get('ENABLE_EXPORT', 'true').lower() == 'true'
ENABLE_COMPARISONS = os.environ.get('ENABLE_COMPARISONS', 'true').lower() == 'true'
ENABLE_PREDICTIONS = os.environ.get('ENABLE_PREDICTIONS', 'false').lower() == 'true'
USE_AWS_SECRETS = os.environ.get('USE_AWS_SECRETS', 'true').lower() == 'true'

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Performance settings
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))
CONNECTION_POOL_SIZE = int(os.environ.get('CONNECTION_POOL_SIZE', '5'))
CONNECTION_POOL_OVERFLOW = int(os.environ.get('CONNECTION_POOL_OVERFLOW', '10'))

def get_database_connection_string() -> str:
    """
    Get database connection string, either from environment or AWS Secrets Manager.
    
    Returns:
        str: PostgreSQL connection string
        
    Raises:
        ValueError: If connection string cannot be determined
    """
    # First, check if we have a direct DATABASE_URL
    if DATABASE_URL:
        logger.info("Using DATABASE_URL from environment")
        return DATABASE_URL
    
    # If all database parameters are provided via environment, build connection string
    if all([DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        from urllib.parse import quote_plus
        encoded_password = quote_plus(DATABASE_PASSWORD)
        connection_string = f"postgresql://{DATABASE_USER}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
        logger.info(f"Using database connection from environment variables: {DATABASE_USER}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")
        return connection_string
    
    # Otherwise, try to fetch from AWS Secrets Manager
    if USE_AWS_SECRETS:
        try:
            logger.info("Fetching database credentials from AWS Secrets Manager")
            from externalconnections.fetch_oura_secrets import get_postgres_credentials, build_postgres_connection_string
            
            postgres_secrets = get_postgres_credentials(
                secret_name=POSTGRES_SECRETS_NAME,
                region_name=AWS_REGION
            )
            
            # Override with environment variables if provided
            if DATABASE_HOST:
                postgres_secrets['host'] = DATABASE_HOST
            if DATABASE_NAME:
                postgres_secrets['database'] = DATABASE_NAME
            if DATABASE_USER:
                postgres_secrets['username'] = DATABASE_USER
            if DATABASE_PASSWORD:
                postgres_secrets['password'] = DATABASE_PASSWORD
                
            connection_string = build_postgres_connection_string(postgres_secrets)
            logger.info("Successfully retrieved database credentials from AWS Secrets Manager")
            return connection_string
            
        except Exception as e:
            logger.error(f"Failed to fetch credentials from AWS Secrets Manager: {e}")
            # Fall back to local defaults for development
            if os.environ.get('ENVIRONMENT', 'production') == 'development':
                logger.warning("Using default local database connection for development")
                return 'postgresql://postgres:password@localhost:5432/oura_health'
            raise
    
    # If we get here, we couldn't determine the connection string
    raise ValueError("Unable to determine database connection string. Please set DATABASE_URL or configure AWS Secrets Manager.")

# Validate configuration at module import
def validate_config():
    """Validate that configuration can be loaded"""
    try:
        # Don't validate database connection at import time to avoid circular imports
        # Just log the configuration status
        logger.info(f"Dashboard configuration initialized")
        logger.info(f"AWS Region: {AWS_REGION}")
        logger.info(f"Use AWS Secrets: {USE_AWS_SECRETS}")
        logger.info(f"Storage Backend: {STORAGE_BACKEND}")
        
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        # Don't fail at import time

# Run validation
validate_config()