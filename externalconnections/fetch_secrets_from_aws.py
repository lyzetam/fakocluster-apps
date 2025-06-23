import sys
import json
import logging
from botocore.exceptions import ClientError
from aws_secrets_manager_client import create_secrets_manager_client

# Dynamically adjust sys.path to include required directories
sys.path.insert(0, '../Scripts')
sys.path.insert(0, '../Scripts/externalconnections')
sys.path.insert(0, '../Scripts/datafetch')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_secret(secret_name):
    """
    Fetch the secret from AWS Secrets Manager and parse it as JSON.

    Args:
        secret_name (str): The name or ARN of the secret to retrieve.

    Returns:
        dict: The parsed secret value as a dictionary.

    Raises:
        ClientError: If an AWS error occurs while retrieving the secret.
        ValueError: If the secret does not contain a valid 'SecretString' or is not valid JSON.
    """
    # Create the Secrets Manager client
    client = create_secrets_manager_client()

    try:
        # Attempt to fetch the secret value from AWS Secrets Manager
        logging.info(f"Fetching secret: {secret_name}")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # Log the error and re-raise it
        logging.error(f"Error retrieving secret '{secret_name}': {e}", exc_info=True)
        raise

    # Extract the SecretString
    secret_string = get_secret_value_response.get('SecretString')
    if not secret_string:
        # Handle cases where the SecretString is empty or invalid
        error_message = f"Secret '{secret_name}' is empty or does not contain a valid 'SecretString'."
        logging.error(error_message)
        raise ValueError(error_message)

    # Parse and return the secret as JSON
    try:
        secret = json.loads(secret_string)
        logging.info(f"Successfully fetched and parsed secret: {secret_name}")
        return secret
    except json.JSONDecodeError as e:
        error_message = f"Error parsing secret '{secret_name}' as JSON: {e}"
        logging.error(error_message)
        raise ValueError(error_message)
