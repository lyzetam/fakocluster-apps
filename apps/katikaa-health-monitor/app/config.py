"""
Configuration management for Katikaa Health Monitor
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for health monitor application"""
    
    def __init__(self):
        self.load_config()
        self.setup_logging()
    
    def load_config(self):
        """Load configuration from environment variables"""
        
        # Database Configuration
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = int(os.getenv('DB_PORT', 3306))
        self.DB_NAME = os.getenv('DB_NAME', 'katikaa_db')
        self.DB_USER = os.getenv('DB_USER', 'katikaa_user')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        
        # External APIs
        self.FAPSHI_PAYMENT_API_USER = os.getenv('FAPSHI_PAYMENT_API_USER', '')
        self.FAPSHI_PAYMENT_API_KEY = os.getenv('FAPSHI_PAYMENT_API_KEY', '')
        self.FAPSHI_CASHOUT_API_USER = os.getenv('FAPSHI_CASHOUT_API_USER', '')
        self.FAPSHI_CASHOUT_API_KEY = os.getenv('FAPSHI_CASHOUT_API_KEY', '')
        self.SPORTMONKS_API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN', '')
        
        # AWS Configuration
        self.AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        
        # Alerting Configuration
        self.SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
        self.NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL', '')
        
        # Health Monitor Configuration
        self.HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 300))
        self.ALERT_THRESHOLD_CRITICAL = int(os.getenv('ALERT_THRESHOLD_CRITICAL', 80))
        self.ALERT_THRESHOLD_WARNING = int(os.getenv('ALERT_THRESHOLD_WARNING', 60))
        
        # Application Configuration
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
        # Redis Configuration
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        self.REDIS_DB = int(os.getenv('REDIS_DB', 0))
        
        # Prometheus Configuration
        self.PROMETHEUS_ENABLED = os.getenv('PROMETHEUS_ENABLED', 'True').lower() == 'true'
        self.PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 8000))
        
        # External API URLs
        self.FAPSHI_BASE_URL = "https://live.fapshi.com"
        self.SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3"
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/app/logs/health_monitor.log') if os.path.exists('/app/logs') else logging.NullHandler()
            ]
        )
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        return {
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'database': self.DB_NAME,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD
        }
    
    def get_fapshi_payment_config(self) -> Dict[str, str]:
        """Get Fapshi payment API configuration"""
        return {
            'base_url': self.FAPSHI_BASE_URL,
            'api_user': self.FAPSHI_PAYMENT_API_USER,
            'api_key': self.FAPSHI_PAYMENT_API_KEY
        }
    
    def get_fapshi_cashout_config(self) -> Dict[str, str]:
        """Get Fapshi cashout API configuration"""
        return {
            'base_url': self.FAPSHI_BASE_URL,
            'api_user': self.FAPSHI_CASHOUT_API_USER,
            'api_key': self.FAPSHI_CASHOUT_API_KEY
        }
    
    def get_sportmonks_config(self) -> Dict[str, str]:
        """Get SportMonks API configuration"""
        return {
            'base_url': self.SPORTMONKS_BASE_URL,
            'api_token': self.SPORTMONKS_API_TOKEN
        }
    
    def get_aws_config(self) -> Dict[str, str]:
        """Get AWS configuration"""
        return {
            'region': self.AWS_REGION,
            'access_key_id': self.AWS_ACCESS_KEY_ID,
            'secret_access_key': self.AWS_SECRET_ACCESS_KEY
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            'host': self.REDIS_HOST,
            'port': self.REDIS_PORT,
            'db': self.REDIS_DB
        }
    
    def get_alert_thresholds(self) -> Dict[str, int]:
        """Get alert thresholds"""
        return {
            'warning': self.ALERT_THRESHOLD_WARNING,
            'critical': self.ALERT_THRESHOLD_CRITICAL
        }
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate critical configuration settings"""
        validation_results = {
            'database': all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]),
            'fapshi_payment': all([self.FAPSHI_PAYMENT_API_USER, self.FAPSHI_PAYMENT_API_KEY]),
            'fapshi_cashout': all([self.FAPSHI_CASHOUT_API_USER, self.FAPSHI_CASHOUT_API_KEY]),
            'sportmonks': bool(self.SPORTMONKS_API_TOKEN),
            'aws': all([self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY]) if any([self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY]) else True
        }
        
        return validation_results
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return not self.DEBUG
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get health check configuration"""
        return {
            'interval': self.HEALTH_CHECK_INTERVAL,
            'thresholds': self.get_alert_thresholds(),
            'notifications': {
                'slack': self.SLACK_WEBHOOK_URL,
                'email': self.NOTIFICATION_EMAIL
            }
        }

# Global config instance
config = Config()
