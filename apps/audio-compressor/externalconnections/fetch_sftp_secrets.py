"""Fetch SFTP credentials from AWS Secrets Manager"""
import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_sftp_credentials(secret_name: str = None, region_name: str = None) -> dict:
    """
    Retrieve SFTP credentials from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region name
        
    Returns:
        Dictionary with 'username' and 'password' keys
        
    Raises:
        Exception: If secrets cannot be retrieved
    """
    from src import config
    
    secret_name = secret_name or config.SFTP_SECRETS_NAME
    region_name = region_name or config.AWS_REGION
    
    logger.info(f"Fetching SFTP credentials from AWS Secrets Manager: {secret_name}")
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise Exception(f"Cannot retrieve SFTP credentials from Secrets Manager: {e}")
    
    # Parse the secret
    secret = get_secret_value_response['SecretString']
    secret_dict = json.loads(secret)
    
    # Extract credentials
    username = secret_dict.get('username') or secret_dict.get('SFTP_USERNAME')
    password = secret_dict.get('password') or secret_dict.get('SFTP_PASSWORD')
    
    if not username or not password:
        raise Exception("SFTP credentials missing 'username' or 'password' in secret")
    
    logger.info("Successfully retrieved SFTP credentials")
    
    return {
        'username': username,
        'password': password
    }
