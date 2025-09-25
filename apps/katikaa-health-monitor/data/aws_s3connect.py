import os
import json
import boto3
import logging
from botocore.exceptions import ClientError

# Add the directory containing aws_secrets_manager_client.py to sys.path
import sys
sys.path.insert(0, '../Scripts/externalconnections')

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class S3ClientCreationError(Exception):
    """Custom exception for errors during S3 client creation."""
    pass

def create_s3_client():
    """
    Create and return an S3 client using credentials from aws_config.json.

    The function reads AWS credentials from a local JSON configuration file,
    validates them, and uses them to create a boto3 S3 client.

    Returns:
        boto3.client: An S3 client configured with the provided credentials.

    Raises:
        FileNotFoundError: If the aws_config.json file is not found.
        ValueError: If the configuration file is missing required keys or contains invalid JSON.
        S3ClientCreationError: If there is an error creating the S3 client.
    """
    # Define the path to the aws_config.json file
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws_config.json')

    # Ensure the configuration file exists
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file 'aws_config.json' not found at {config_path}")

    # Load and validate AWS credentials from the configuration file
    try:
        with open(config_path, 'r') as config_file:
            aws_creds = json.load(config_file)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration file: {e}")
        raise ValueError(f"Invalid JSON in configuration file 'aws_config.json': {e}")

    # Validate required keys
    required_keys = ['aws_access_key_id', 'aws_secret_access_key', 'region']
    missing_keys = [key for key in required_keys if key not in aws_creds]
    if missing_keys:
        logging.error(f"Missing required keys in aws_config.json: {', '.join(missing_keys)}")
        raise ValueError(f"Missing required keys in aws_config.json: {', '.join(missing_keys)}")

    # Validate credential values are not empty
    for key in required_keys:
        if not aws_creds[key]:
            logging.error(f"Credential '{key}' is empty in aws_config.json.")
            raise ValueError(f"Credential '{key}' cannot be empty in aws_config.json.")

    # Create and return the S3 client
    try:
        logging.info("Creating S3 client with the provided credentials.")
        return boto3.client(
            's3',
            aws_access_key_id=aws_creds['aws_access_key_id'],
            aws_secret_access_key=aws_creds['aws_secret_access_key'],
            region_name=aws_creds['region']
        )
    except ClientError as e:
        logging.error(f"Error creating S3 client: {e}")
        raise S3ClientCreationError("Failed to create S3 client. Please check AWS credentials and network connectivity.") from e

