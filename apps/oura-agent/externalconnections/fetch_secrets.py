"""Fetch secrets from AWS Secrets Manager for Oura Health Agent."""

import json
import logging
import os
from urllib.parse import quote_plus

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, region_name: str = None) -> dict:
    """Fetch a secret from AWS Secrets Manager.

    Args:
        secret_name: The name or ARN of the secret to retrieve
        region_name: AWS region name (defaults to AWS_DEFAULT_REGION env var)

    Returns:
        dict: The parsed secret value as a dictionary

    Raises:
        ClientError: If an AWS error occurs while retrieving the secret
        ValueError: If the secret is invalid
    """
    region = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)

    try:
        logger.info(f"Fetching secret: {secret_name}")
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Error retrieving secret '{secret_name}': {e}")
        raise

    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret '{secret_name}' is empty or invalid")

    try:
        secret = json.loads(secret_string)
        logger.info(f"Successfully fetched secret: {secret_name}")
        return secret
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing secret '{secret_name}' as JSON: {e}")


def get_discord_secrets(secret_name: str = "oura-agent/discord") -> dict:
    """Fetch Discord bot credentials from AWS Secrets Manager.

    Expected secret format:
    {
        "bot_token": "YOUR_BOT_TOKEN",
        "guild_id": "1449776768725553386",
        "health_channel_id": "1449859614295199744"
    }

    Falls back to environment variables if AWS fetch fails.
    """
    try:
        return get_secret(secret_name)
    except Exception as e:
        logger.warning(f"Could not fetch Discord secrets from AWS: {e}")
        return {
            "bot_token": os.getenv("DISCORD_BOT_TOKEN"),
            "guild_id": os.getenv("DISCORD_GUILD_ID"),
            "health_channel_id": os.getenv("DISCORD_HEALTH_CHANNEL_ID"),
        }


def get_anthropic_secrets(secret_name: str = "oura-agent/anthropic") -> dict:
    """Fetch Anthropic API credentials from AWS Secrets Manager.

    Expected secret format:
    {
        "api_key": "sk-ant-..."
    }

    Falls back to environment variables if AWS fetch fails.
    """
    try:
        return get_secret(secret_name)
    except Exception as e:
        logger.warning(f"Could not fetch Anthropic secrets from AWS: {e}")
        return {"api_key": os.getenv("ANTHROPIC_API_KEY")}


def get_database_secrets(secret_name: str = "postgres/app-user") -> dict:
    """Fetch PostgreSQL credentials from AWS Secrets Manager.

    Expected secret format:
    {
        "username": "your_username",
        "password": "your_password",
        "host": "your-database-host",
        "port": 5432,
        "database": "oura_health"
    }

    Prefers DATABASE_URL environment variable if available (for K8s deployments),
    then falls back to AWS Secrets Manager.
    """
    # Prefer DATABASE_URL env var for K8s deployments with ExternalSecrets
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        logger.info("Using DATABASE_URL from environment")
        return {"connection_string": db_url}

    # Fall back to AWS Secrets Manager
    try:
        return get_secret(secret_name)
    except Exception as e:
        logger.warning(f"Could not fetch database secrets from AWS: {e}")
        return {}


def get_ollama_secrets(secret_name: str = "ollama/endpoint") -> dict:
    """Fetch Ollama endpoint configuration from AWS Secrets Manager.

    Expected secret format:
    {
        "base_url": "http://ollama.ai-ml.svc.cluster.local:11434"
    }

    Falls back to environment variables if AWS fetch fails.
    """
    try:
        return get_secret(secret_name)
    except Exception as e:
        logger.warning(f"Could not fetch Ollama secrets from AWS: {e}")
        return {"base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")}


def build_postgres_connection_string(credentials: dict) -> str:
    """Build a PostgreSQL connection string from credentials.

    Args:
        credentials: Dictionary containing database credentials

    Returns:
        str: PostgreSQL connection string (async compatible with asyncpg)
    """
    # If connection_string is directly provided
    if "connection_string" in credentials:
        conn_str = credentials["connection_string"]
        # Convert to async driver if needed
        if conn_str.startswith("postgresql://"):
            return conn_str.replace("postgresql://", "postgresql+asyncpg://")
        return conn_str

    username = credentials.get("username")
    password = credentials.get("password")
    host = credentials.get("host")
    port = credentials.get("port", 5432)
    database = credentials.get("database", "oura_health")

    if not all([username, password, host]):
        raise ValueError("Missing required database credentials")

    # URL encode the password to handle special characters
    encoded_password = quote_plus(password)

    return f"postgresql+asyncpg://{username}:{encoded_password}@{host}:{port}/{database}"
