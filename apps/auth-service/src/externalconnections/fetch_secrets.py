"""Fetch secrets from AWS Secrets Manager for Auth Service"""
import json
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_secret(secret_name: str, region_name: str = "us-east-1") -> dict:
    """
    Fetch a secret from AWS Secrets Manager.
    
    Args:
        secret_name: The name or ARN of the secret to retrieve
        region_name: AWS region name
        
    Returns:
        dict: The parsed secret value as a dictionary
        
    Raises:
        ClientError: If an AWS error occurs while retrieving the secret
        ValueError: If the secret is invalid
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        logger.info(f"Fetching secret: {secret_name}")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Error retrieving secret '{secret_name}': {e}")
        raise
    
    # Extract and parse the secret
    secret_string = get_secret_value_response.get('SecretString')
    if not secret_string:
        error_message = f"Secret '{secret_name}' is empty or invalid"
        logger.error(error_message)
        raise ValueError(error_message)
    
    try:
        secret = json.loads(secret_string)
        logger.info(f"Successfully fetched secret: {secret_name}")
        return secret
    except json.JSONDecodeError as e:
        error_message = f"Error parsing secret '{secret_name}' as JSON: {e}"
        logger.error(error_message)
        raise ValueError(error_message)

def get_postgres_credentials(secret_name: str = "auth-service/postgres",
                           region_name: str = "us-east-1") -> dict:
    """
    Fetch PostgreSQL credentials from AWS Secrets Manager.
    
    Expected secret format:
    {
        "username": "auth_service_user",
        "password": "your_password",
        "host": "your-database-host.region.rds.amazonaws.com",
        "port": 5432,
        "database": "auth_service"
    }
    """
    return get_secret(secret_name, region_name)

def get_api_key_config(secret_name: str = "auth-service/api-keys",
                      region_name: str = "us-east-1") -> dict:
    """
    Fetch API key configuration from AWS Secrets Manager.
    
    Expected secret format:
    {
        "master_api_key": "your-master-api-key",
        "admin_api_keys": {
            "admin-key-1": {
                "name": "Main Admin Key",
                "email": "admin@example.com",
                "is_admin": true
            }
        }
    }
    """
    return get_secret(secret_name, region_name)

def build_postgres_connection_string(credentials: dict) -> str:
    """
    Build a PostgreSQL connection string from credentials.
    
    Args:
        credentials: Dictionary containing database credentials
        
    Returns:
        str: PostgreSQL connection string
    """
    username = credentials.get('username')
    password = credentials.get('password')
    host = credentials.get('host')
    port = credentials.get('port', 5432)
    database = credentials.get('database', 'auth_service')
    
    if not all([username, password, host]):
        raise ValueError("Missing required database credentials")
    
    # URL encode the password to handle special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(password)
    
    return f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}"