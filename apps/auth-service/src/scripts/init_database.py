#!/usr/bin/env python3
"""Initialize Auth Service database schema"""
import sys
import logging
import argparse
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from sqlalchemy import create_engine, text
from auth.database_models import Base
from externalconnections.fetch_secrets import get_postgres_credentials, build_postgres_connection_string
from auth import config

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
    
    # Create additional indexes
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Ensure we're not in a transaction
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_access_log_email_app_time ON auth_access_logs(email, app_name, access_time DESC)",
            "CREATE INDEX IF NOT EXISTS idx_access_log_denied_time ON auth_access_logs(access_granted, access_time DESC) WHERE access_granted = false",
            "CREATE INDEX IF NOT EXISTS idx_audit_target_email ON auth_audit_logs(target_email, action_time DESC)",
            "CREATE INDEX IF NOT EXISTS idx_permission_active_expires ON auth_user_app_permissions(is_active, expires_at) WHERE is_active = true"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                logger.warning(f"Index might already exist: {e}")

def main():
    parser = argparse.ArgumentParser(description='Initialize Auth Service database')
    parser.add_argument('--connection-string', help='PostgreSQL connection string (overrides AWS secrets)')
    parser.add_argument('--create-db', action='store_true', help='Create database if it doesn\'t exist')
    args = parser.parse_args()
    
    try:
        if args.connection_string:
            connection_string = args.connection_string
            database_name = connection_string.split('/')[-1].split('?')[0]
        else:
            # Load from AWS Secrets Manager
            postgres_secrets = get_postgres_credentials(
                secret_name=config.POSTGRES_SECRETS_NAME,
                region_name=config.AWS_REGION
            )
            connection_string = build_postgres_connection_string(postgres_secrets)
            database_name = postgres_secrets.get('database', 'auth_service')
        
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