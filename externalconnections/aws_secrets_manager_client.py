# Add the directory containing aws_secrets_manager_client.py to sys.path
import sys
sys.path.insert(0, '../Scripts')
sys.path.insert(0, '../Scripts/externalconnections')
sys.path.insert(0, '../Scripts/datafetch')

import os
import json
import boto3


def create_secrets_manager_client():
    """
    Create and return a Secrets Manager client using credentials from aws_config.json.
    The function connects to AWS Secrets Manager using credentials and configurations from a JSON file (aws_config.json).
    """
    # Determine the path to the configuration file
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aws_config.json')

    # Verify if the configuration file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file 'aws_config.json' not found at {config_path}")

    # Load credentials from the aws_config.json file
    try:
        with open(config_path, 'r') as config_file:
            aws_creds = json.load(config_file)
    except json.JSONDecodeError:
        raise ValueError(f"Configuration file 'aws_config.json' contains invalid JSON at {config_path}")

    # Validate required fields in the configuration
    required_keys = ['aws_access_key_id', 'aws_secret_access_key', 'region']
    missing_keys = [key for key in required_keys if key not in aws_creds]
    if missing_keys:
        raise KeyError(f"Missing required keys in aws_config.json: {', '.join(missing_keys)}")

    # Create and return the Secrets Manager client
    return boto3.client(
        'secretsmanager',
        aws_access_key_id=aws_creds['aws_access_key_id'],
        aws_secret_access_key=aws_creds['aws_secret_access_key'],
        region_name=aws_creds['region']
    )
