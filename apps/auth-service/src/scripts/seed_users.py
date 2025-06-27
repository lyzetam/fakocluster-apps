#!/usr/bin/env python3
"""Seed Auth Service database with an initial admin user and API key."""
import sys
import os
import argparse
import logging
import secrets
import hashlib

# Allow imports from auth service modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.database_models import AuthorizedUser, ApiKey
from externalconnections.fetch_secrets import (
    get_postgres_credentials,
    build_postgres_connection_string,
)
from auth import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Function to seed admin user and optional API key

def seed_admin(
    connection_string: str,
    email: str,
    create_api_key: bool = False,
    api_key_name: str = "Initial Admin Key",
) -> None:
    """Create the default admin user and optional API key."""
    engine = create_engine(connection_string)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        user = (
            session.query(AuthorizedUser)
            .filter(AuthorizedUser.email == email.lower())
            .first()
        )
        if user:
            logger.info("Admin user %s already exists", email)
        else:
            user = AuthorizedUser(
                email=email.lower(),
                full_name="Admin",
                is_admin=True,
                created_by=email.lower(),
                notes="Seeded admin user",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Created admin user %s", email)

        if create_api_key:
            token = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(token.encode()).hexdigest()
            api_record = ApiKey(
                key_hash=key_hash,
                name=api_key_name,
                created_by=user.email,
                is_admin=True,
            )
            session.add(api_record)
            session.commit()
            logger.info("Created admin API key '%s'", api_key_name)
            print(f"Generated API key: {token}")
    except Exception as exc:
        session.rollback()
        logger.error("Failed to seed admin user: %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the database with an initial admin user"
    )
    parser.add_argument(
        "--email",
        default=config.DEFAULT_ADMIN_EMAIL,
        help="Admin email address",
    )
    parser.add_argument(
        "--postgres-secret-name",
        default=config.POSTGRES_SECRETS_NAME,
        help="Name of the secret storing Postgres credentials",
    )
    parser.add_argument(
        "--aws-region",
        default=config.AWS_REGION,
        help="AWS region for Secrets Manager",
    )
    parser.add_argument(
        "--connection-string",
        help="PostgreSQL connection string (overrides secrets)",
    )
    parser.add_argument(
        "--create-api-key",
        action="store_true",
        help="Generate an initial admin API key",
    )
    parser.add_argument(
        "--api-key-name",
        default="Initial Admin Key",
        help="Name for the generated admin API key",
    )

    args = parser.parse_args()

    if args.connection_string:
        connection_string = args.connection_string
    else:
        postgres_secrets = get_postgres_credentials(
            secret_name=args.postgres_secret_name,
            region_name=args.aws_region,
        )
        connection_string = build_postgres_connection_string(postgres_secrets)

    seed_admin(
        connection_string,
        args.email,
        create_api_key=args.create_api_key,
        api_key_name=args.api_key_name,
    )


if __name__ == "__main__":
    main()
