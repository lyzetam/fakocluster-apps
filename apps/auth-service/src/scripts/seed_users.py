#!/usr/bin/env python3
"""Seed Auth Service database with an initial admin user."""
import sys
import os
import argparse
import logging

# Allow imports from auth service modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.database_models import AuthorizedUser
from externalconnections.fetch_secrets import get_postgres_credentials, build_postgres_connection_string
from auth import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_admin_user(connection_string: str, email: str, password: str) -> None:
    """Insert an admin user if one does not already exist."""
    engine = create_engine(connection_string)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()
    try:
        existing = session.query(AuthorizedUser).filter(AuthorizedUser.email == email.lower()).first()
        if existing:
            logger.info("User %s already exists", email)
            return

        user = AuthorizedUser(
            email=email.lower(),
            full_name="Admin",
            is_admin=True,
            created_by=email.lower(),
            notes="Seeded admin user"
        )
        session.add(user)
        session.commit()
        logger.info("Created admin user %s", email)
    except Exception as exc:
        session.rollback()
        logger.error("Failed to create admin user: %s", exc)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with an initial admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--connection-string", help="PostgreSQL connection string (overrides AWS secrets)")
    args = parser.parse_args()

    if args.connection_string:
        connection_string = args.connection_string
    else:
        postgres_secrets = get_postgres_credentials(
            secret_name=config.POSTGRES_SECRETS_NAME,
            region_name=config.AWS_REGION,
        )
        connection_string = build_postgres_connection_string(postgres_secrets)

    add_admin_user(connection_string, args.email, args.password)


if __name__ == "__main__":
    main()
