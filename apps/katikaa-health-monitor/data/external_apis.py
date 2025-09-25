"""
External API connections for Katikaa Health Monitor
Based on Scripts/externalconnections functionality
"""

import logging
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from app.config import config

logger = logging.getLogger(__name__)

class FapshiPaymentAPI:
    """Fapshi Payment API integration"""
    
    def __init__(self):
        fapshi_config = config.get_fapshi_payment_config()
        self.base_url = fapshi_config['base_url']
        self.api_user = fapshi_config['api_user']
        self.api_key = fapshi_config['api_key']
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get Fapshi account balance"""
        try:
            url = f"{self.base_url}/api/balance"
            auth_data = {
                'apiuser': self.api_user,
                'apikey': self.api_key
            }
            
            response = self.session.post(url, json=auth_data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Fapshi balance: {e}")
            return {'error': str(e)}
    
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction status from Fapshi"""
        try:
            url = f"{self.base_url}/api/transaction/status"
            data = {
                'apiuser': self.api_user,
                'apikey': self.api_key,
                'transaction_id': transaction_id
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Fapshi transaction status: {e}")
            return {'error': str(e)}
    
    def get_payment_health_metrics(self) -> Dict[str, Any]:
        """Get payment gateway health metrics"""
        try:
            balance_info = self.get_account_balance()
            
            # Calculate health metrics
            metrics = {
                'balance': balance_info.get('balance', 0),
                'currency': balance_info.get('currency', 'FCFA'),
                'status': 'healthy' if 'error' not in balance_info else 'error',
                'last_check': datetime.now().isoformat()
            }
            
            # Add more health checks as needed
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting payment health metrics: {e}")
            return {'error': str(e)}

class FapshiCashoutAPI:
    """Fapshi Cashout API integration"""
    
    def __init__(self):
        fapshi_config = config.get_fapshi_cashout_config()
        self.base_url = fapshi_config['base_url']
        self.api_user = fapshi_config['api_user']
        self.api_key = fapshi_config['api_key']
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_cashout_status(self, cashout_id: str) -> Dict[str, Any]:
        """Get cashout status"""
        try:
            url = f"{self.base_url}/api/cashout/status"
            data = {
                'apiuser': self.api_user,
                'apikey': self.api_key,
                'cashout_id': cashout_id
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting cashout status: {e}")
            return {'error': str(e)}
    
    def get_cashout_health_metrics(self) -> Dict[str, Any]:
        """Get cashout system health metrics"""
        try:
            # This would implement actual cashout health checks
            metrics = {
                'service_status': 'operational',
                'last_check': datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting cashout health metrics: {e}")
            return {'error': str(e)}

class SportMonksAPI:
    """SportMonks API integration"""
    
    def __init__(self):
        sportmonks_config = config.get_sportmonks_config()
        self.base_url = sportmonks_config['base_url']
        self.api_token = sportmonks_config['api_token']
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        })
    
    def get_api_usage(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        try:
            url = f"{self.base_url}/my/usage"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting SportMonks API usage: {e}")
            return {'error': str(e)}
    
    def get_fixtures(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get fixtures for a specific date"""
        try:
            url = f"{self.base_url}/fixtures"
            params = {}
            if date:
                params['date'] = date
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting fixtures: {e}")
            return {'error': str(e)}
    
    def get_api_health_metrics(self) -> Dict[str, Any]:
        """Get API health metrics"""
        try:
            usage_info = self.get_api_usage()
            
            if 'error' in usage_info:
                return usage_info
            
            # Calculate health metrics based on usage
            usage_data = usage_info.get('data', {})
            total_requests = usage_data.get('total_requests', 0)
            remaining_requests = usage_data.get('remaining_requests', 0)
            request_limit = usage_data.get('request_limit', 1)
            
            usage_percentage = ((total_requests) / request_limit) * 100 if request_limit > 0 else 0
            
            metrics = {
                'total_requests': total_requests,
                'remaining_requests': remaining_requests,
                'request_limit': request_limit,
                'usage_percentage': usage_percentage,
                'status': 'healthy' if usage_percentage < 90 else 'warning',
                'last_check': datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting API health metrics: {e}")
            return {'error': str(e)}

class AWSSecretsManager:
    """AWS Secrets Manager integration"""
    
    def __init__(self):
        aws_config = config.get_aws_config()
        self.region = aws_config['region']
        self.access_key_id = aws_config['access_key_id']
        self.secret_access_key = aws_config['secret_access_key']
        
        self.client = None
        if self.access_key_id and self.secret_access_key:
            self.client = boto3.client(
                'secretsmanager',
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key
            )
    
    def get_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a secret from AWS Secrets Manager"""
        if not self.client:
            logger.warning("AWS client not configured")
            return None
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response.get('SecretString')
            
            if secret_string:
                return json.loads(secret_string)
            
            return None
            
        except ClientError as e:
            logger.error(f"Error retrieving secret {secret_name}: {e}")
            return None
    
    def list_secrets(self) -> List[str]:
        """List all available secrets"""
        if not self.client:
            return []
        
        try:
            response = self.client.list_secrets()
            return [secret['Name'] for secret in response.get('SecretList', [])]
            
        except ClientError as e:
            logger.error(f"Error listing secrets: {e}")
            return []

class NotificationService:
    """Notification service for alerts and health updates"""
    
    def __init__(self):
        self.slack_webhook_url = config.SLACK_WEBHOOK_URL
        self.notification_email = config.NOTIFICATION_EMAIL
        self.session = requests.Session()
    
    def send_slack_notification(self, message: str, channel: Optional[str] = None) -> bool:
        """Send notification to Slack"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            payload = {
                'text': message,
                'username': 'Katikaa Health Monitor'
            }
            
            if channel:
                payload['channel'] = channel
            
            response = self.session.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def send_health_alert(self, alert_type: str, message: str, severity: str = 'warning') -> bool:
        """Send health alert notification"""
        try:
            formatted_message = f"🚨 *{alert_type.upper()} ALERT* ({severity.upper()})\n{message}"
            
            # Send to Slack
            slack_sent = self.send_slack_notification(formatted_message)
            
            # Could add email notifications here
            
            return slack_sent
            
        except Exception as e:
            logger.error(f"Error sending health alert: {e}")
            return False

# Global API clients
fapshi_payment_api = FapshiPaymentAPI()
fapshi_cashout_api = FapshiCashoutAPI()
sportmonks_api = SportMonksAPI()
aws_secrets_manager = AWSSecretsManager()
notification_service = NotificationService()
