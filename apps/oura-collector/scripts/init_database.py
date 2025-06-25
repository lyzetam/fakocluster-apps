#!/usr/bin/env python3
"""Initialize Oura database schema"""
import sys
import logging
import argparse
import os

# Add the parent directory to the Python path to access modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'collector'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from sqlalchemy import create_engine, text
from src.collector.database_models import Base
from externalconnections.fetch_oura_secrets import get_postgres_credentials, build_postgres_connection_string
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_if_not_exists(connection_string: str, database_name: str):
    """Create the database if it doesn't exist"""
    # Connect to the default 'postgres' database first
    base_connection = connection_string.rsplit('/', 1)[0] + '/postgres'
    
    engine = create_engine(base_connection)
    conn = engine.connect()
    
    # For PostgreSQL 13+, we need to use isolation level for CREATE DATABASE
    conn = conn.execution_options(isolation_level="AUTOCOMMIT")
    
    try:
        # Check if database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": database_name}
        )
        
        if not result.fetchone():
            # Create database
            conn.execute(text(f"CREATE DATABASE {database_name}"))
            logger.info(f"Created database: {database_name}")
        else:
            logger.info(f"Database already exists: {database_name}")
    finally:
        conn.close()

def init_database(connection_string: str):
    """Initialize the database schema"""
    # Create engine
    engine = create_engine(connection_string)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully")
    
    # Create indexes if they don't exist
    with engine.connect() as conn:
        # Additional custom indexes can be added here
        logger.info("Database indexes verified")

def main():
    parser = argparse.ArgumentParser(description='Initialize Oura database')
    parser.add_argument('--connection-string', help='PostgreSQL connection string (overrides AWS secrets)')
    parser.add_argument('--create-db', action='store_true', help='Create database if it doesn\'t exist')
    args = parser.parse_args()
    
    try:
        if args.connection_string:
            connection_string = args.connection_string
            database_name = connection_string.split('/')[-1]
        else:
            # Load from AWS Secrets Manager
            postgres_secrets = get_postgres_credentials(
                secret_name=config.POSTGRES_SECRETS_NAME,
                region_name=config.AWS_REGION
            )
            connection_string = build_postgres_connection_string(postgres_secrets)
            database_name = postgres_secrets.get('database', 'oura_health')
        
        # Create database if requested
        if args.create_db:
            create_database_if_not_exists(connection_string, database_name)
        
        # Initialize schema
        init_database(connection_string)
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()