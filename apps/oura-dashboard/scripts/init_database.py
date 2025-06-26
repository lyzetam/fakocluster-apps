#!/usr/bin/env python3
"""Initialize Oura database schema from dashboard (read-only verification)"""
import sys
import logging
import argparse
import os

# Add the parent directory to the Python path to access modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from sqlalchemy import create_engine, inspect
from src.dashboard.database_models import Base
from src.dashboard.config import get_database_connection_string
from externalconnections.fetch_oura_secrets import get_postgres_credentials, build_postgres_connection_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_database_schema(connection_string: str):
    """Verify the database schema exists and is accessible"""
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    
    # Get all table names
    table_names = inspector.get_table_names()
    
    # Expected tables
    expected_tables = [
        'oura_personal_info',
        'oura_sleep_periods', 
        'oura_daily_sleep',
        'oura_activity',
        'oura_readiness',
        'oura_workouts',
        'oura_stress',
        'oura_heart_rate',
        'oura_daily_summaries',
        'oura_collection_logs'
    ]
    
    logger.info(f"Found {len(table_names)} tables in database")
    
    missing_tables = []
    for table in expected_tables:
        if table in table_names:
            logger.info(f"✓ Table exists: {table}")
        else:
            logger.warning(f"✗ Table missing: {table}")
            missing_tables.append(table)
    
    if missing_tables:
        logger.error(f"Missing {len(missing_tables)} tables. Please run the collector's init_database.py script.")
        return False
    else:
        logger.info("All required tables exist!")
        return True

def test_connection(connection_string: str):
    """Test database connection"""
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
        logger.info("Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Verify Oura database for dashboard')
    parser.add_argument('--connection-string', help='PostgreSQL connection string (overrides AWS secrets)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify schema, do not create tables')
    args = parser.parse_args()
    
    try:
        if args.connection_string:
            connection_string = args.connection_string
        else:
            # Use the config function to get connection string
            connection_string = get_database_connection_string()
        
        # Test connection
        if not test_connection(connection_string):
            sys.exit(1)
        
        # Verify schema
        if verify_database_schema(connection_string):
            logger.info("Database verification completed successfully")
        else:
            logger.error("Database verification failed")
            logger.info("Please run: python apps/oura-collector/scripts/init_database.py --create-db")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()