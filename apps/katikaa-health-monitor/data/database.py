"""
Database connection and management for Katikaa Health Monitor
Based on Scripts/datafetch functionality
"""

import logging
import mysql.connector
from mysql.connector import Error
import pandas as pd
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import time
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and query management"""
    
    def __init__(self):
        self.connection_config = self._get_database_config()
        self.connection = None
        self.connection_pool = None
        self._setup_connection_pool()
    
    def _get_database_config(self) -> Dict[str, Any]:
        """Get database configuration from environment variables"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_NAME', 'katikaa_db'),
            'user': os.getenv('DB_USER', 'katikaa_user'),
            'password': os.getenv('DB_PASSWORD', '')
        }
    
    def _setup_connection_pool(self):
        """Setup MySQL connection pool for better performance"""
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="katikaa_pool",
                pool_size=5,
                pool_reset_session=True,
                **self.connection_config
            )
            logger.info("Database connection pool established")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            self.connection_pool = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            if self.connection_pool:
                connection = self.connection_pool.get_connection()
            else:
                connection = mysql.connector.connect(**self.connection_config)
            
            yield connection
            
        except Error as e:
            logger.error(f"Database connection error: {e}")
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params)
                results = cursor.fetchall()
                cursor.close()
                return results
                
        except Error as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in execute_query: {e}")
            return []
    
    def execute_query_df(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as pandas DataFrame
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
                return df
                
        except Error as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            logger.error(f"Query: {query}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error in execute_query_df: {e}")
            return pd.DataFrame()
    
    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> bool:
        """
        Execute INSERT, UPDATE, DELETE queries
        Returns True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                cursor.close()
                return True
                
        except Error as e:
            logger.error(f"Error executing non-query: {e}")
            logger.error(f"Query: {query}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in execute_non_query: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        query = f"DESCRIBE {table_name}"
        return self.execute_query(query)
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def get_tables_list(self) -> List[str]:
        """Get list of all tables in the database"""
        query = "SHOW TABLES"
        results = self.execute_query(query)
        if results:
            # Get the key name dynamically (it varies by database)
            key = list(results[0].keys())[0]
            return [row[key] for row in results]
        return []
    
    # Katikaa-specific data fetching methods
    def get_wallet_transactions(self, limit: int = 1000, days_back: int = 30) -> pd.DataFrame:
        """
        Get wallet transaction data
        Based on Scripts/datafetch logic
        """
        query = """
        SELECT 
            user_id, type, amount, currency_type, source, status,
            created_at, updated_at, description
        FROM prediction_db_wallet_data_df 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY created_at DESC
        LIMIT %s
        """
        return self.execute_query_df(query, (days_back, limit))
    
    def get_user_data(self, limit: int = 1000) -> pd.DataFrame:
        """Get user data"""
        query = """
        SELECT 
            user_id, user_name, email_id, phone_number, 
            registration_date, last_login, status
        FROM prediction_db_user_data_df
        WHERE status = 'ACTIVE'
        ORDER BY registration_date DESC
        LIMIT %s
        """
        return self.execute_query_df(query, (limit,))
    
    def get_prediction_data(self, limit: int = 1000, days_back: int = 30) -> pd.DataFrame:
        """Get prediction data"""
        query = """
        SELECT 
            prediction_id, user_id, community_id, fixture_id,
            prediction_type, predicted_outcome, actual_outcome,
            total_points, creation_date, status
        FROM prediction_db_prediction_data_df
        WHERE creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY creation_date DESC
        LIMIT %s
        """
        return self.execute_query_df(query, (days_back, limit))
    
    def get_community_data(self) -> pd.DataFrame:
        """Get community data"""
        query = """
        SELECT 
            community_id, community_name, description, 
            created_by, creation_date, member_count, status
        FROM prediction_db_community_data_df
        WHERE status = 'ACTIVE'
        ORDER BY member_count DESC
        """
        return self.execute_query_df(query)
    
    def get_commission_data(self, days_back: int = 30) -> pd.DataFrame:
        """Get commission data"""
        query = """
        SELECT 
            commission_id, user_id, community_id, commission_amount,
            currency_type, source, created_at, status
        FROM site_commission_view_data_df
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY created_at DESC
        """
        return self.execute_query_df(query, (days_back,))
    
    def get_fixture_data(self, days_back: int = 7) -> pd.DataFrame:
        """Get fixture data for recent matches"""
        query = """
        SELECT 
            fixture_id, league_id, home_team, away_team,
            match_date, status, home_score, away_score
        FROM fixture_data_df
        WHERE match_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY match_date DESC
        """
        return self.execute_query_df(query, (days_back,))
    
    # Health check queries
    def get_database_health_metrics(self) -> Dict[str, Any]:
        """Get database health metrics"""
        metrics = {}
        
        try:
            # Connection status
            metrics['connection_status'] = self.test_connection()
            
            # Table counts
            tables = [
                'prediction_db_wallet_data_df',
                'prediction_db_user_data_df', 
                'prediction_db_prediction_data_df',
                'prediction_db_community_data_df',
                'site_commission_view_data_df'
            ]
            
            for table in tables:
                try:
                    metrics[f'{table}_count'] = self.get_table_count(table)
                except:
                    metrics[f'{table}_count'] = 0
            
            # Recent activity
            recent_transactions = self.execute_query("""
                SELECT COUNT(*) as count FROM prediction_db_wallet_data_df 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            metrics['recent_transactions'] = recent_transactions[0]['count'] if recent_transactions else 0
            
            recent_predictions = self.execute_query("""
                SELECT COUNT(*) as count FROM prediction_db_prediction_data_df 
                WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            metrics['recent_predictions'] = recent_predictions[0]['count'] if recent_predictions else 0
            
        except Exception as e:
            logger.error(f"Error getting database health metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def close_pool(self):
        """Close connection pool"""
        if self.connection_pool:
            try:
                # Close all connections in the pool
                for _ in range(self.connection_pool.pool_size):
                    try:
                        conn = self.connection_pool.get_connection()
                        conn.close()
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

# Global database manager instance
db_manager = DatabaseManager()
