"""Configuration for Auth Service"""
import os

# AWS Configuration
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
POSTGRES_SECRETS_NAME = os.environ.get('AUTH_POSTGRES_SECRETS_NAME', 'auth-service/postgres')
API_SECRETS_NAME = os.environ.get('AUTH_API_SECRETS_NAME', 'auth-service/api-keys')

# Database Configuration
DATABASE_HOST = os.environ.get('DATABASE_HOST', None)
DATABASE_PORT = os.environ.get('DATABASE_PORT', '5432')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'auth_service')

# API Configuration
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('API_PORT', '8000'))
API_PREFIX = os.environ.get('API_PREFIX', '/api/v1')

# Security Configuration
ENABLE_API_KEY_AUTH = os.environ.get('ENABLE_API_KEY_AUTH', 'true').lower() == 'true'
API_KEY_HEADER = os.environ.get('API_KEY_HEADER', 'X-API-Key')
BCRYPT_ROUNDS = int(os.environ.get('BCRYPT_ROUNDS', '12'))

# Cache Configuration
ENABLE_CACHING = os.environ.get('ENABLE_CACHING', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '300'))  # 5 minutes
NEGATIVE_CACHE_TTL_SECONDS = int(os.environ.get('NEGATIVE_CACHE_TTL_SECONDS', '60'))  # 1 minute for denied access

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')  # 'json' or 'text'

# Health Check Configuration
HEALTH_CHECK_PORT = int(os.environ.get('HEALTH_CHECK_PORT', '8080'))

# Rate Limiting
ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '100'))

# Audit Configuration
ENABLE_AUDIT_LOG = os.environ.get('ENABLE_AUDIT_LOG', 'true').lower() == 'true'
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '90'))

# Default Admin User (for initial setup)
DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')

# CORS Configuration
CORS_ENABLED = os.environ.get('CORS_ENABLED', 'true').lower() == 'true'
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Session Configuration
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', '60'))

# Performance Configuration
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))
CONNECTION_POOL_SIZE = int(os.environ.get('CONNECTION_POOL_SIZE', '10'))
CONNECTION_POOL_OVERFLOW = int(os.environ.get('CONNECTION_POOL_OVERFLOW', '20'))