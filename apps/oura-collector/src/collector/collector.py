#!/usr/bin/env python3
"""Enhanced Oura data collector with PostgreSQL support - FIXED VERSION"""
import sys
import os
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Import configuration - use relative imports since we're in src/collector/
import config

# Import modules
from externalconnections.fetch_oura_secrets import get_oura_credentials, get_postgres_credentials, build_postgres_connection_string
from oura_client import OuraAPIClient
from data_processor import DataProcessor
from storage import DataStorage
from postgres_storage import PostgresStorage
from healthcheck import HealthStatus, start_health_server


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class OuraCollector:
    """Enhanced collector that orchestrates comprehensive data collection"""
    
    def __init__(self):
        """Initialize the collector"""
        logger.info("Initializing Enhanced Oura Collector")
        
        # Start health check server
        self.health_server = start_health_server(port=8080)
        logger.info("Health check server started")
        
        # Initialize health status
        self.health_status = HealthStatus()
        
        # Load configuration from AWS Secrets Manager
        self.config = self._load_configuration()
        
        # Initialize components
        self.oura_client = OuraAPIClient(self.config['oura_token'])
        self.processor = DataProcessor()
        
        # Initialize storage based on backend type
        if config.STORAGE_BACKEND.lower() == 'postgres':
            logger.info("Using PostgreSQL storage backend")
            self.storage = PostgresStorage(self.config['postgres_connection_string'])
        else:
            logger.info("Using file storage backend")
            self.storage = DataStorage(
                data_dir=config.DATA_DIR,
                output_format=config.OUTPUT_FORMAT
            )
        
        # Test connection
        if not self.oura_client.test_connection():
            raise RuntimeError("Failed to connect to Oura API")
        
        logger.info("Enhanced Oura Collector initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from AWS Secrets Manager
        
        Returns:
            Configuration dictionary
        """
        try:
            # Get Oura credentials
            oura_secrets = get_oura_credentials(
                secret_name=config.OURA_SECRETS_NAME,
                region_name=config.AWS_REGION
            )
            
            # Required Oura configuration
            if 'oura_personal_access_token' not in oura_secrets:
                raise ValueError("oura_personal_access_token not found in Oura secrets")
            
            configuration = {
                'oura_token': oura_secrets['oura_personal_access_token'],
                'collection_interval': oura_secrets.get('collection_interval', config.COLLECTION_INTERVAL),
                'days_to_backfill': oura_secrets.get('days_to_backfill', config.DAYS_TO_BACKFILL),
                'collect_all_endpoints': oura_secrets.get('collect_all_endpoints', True),
                'endpoints_to_collect': oura_secrets.get('endpoints_to_collect', [])
            }
            
            # Get PostgreSQL credentials if using postgres backend
            if config.STORAGE_BACKEND.lower() == 'postgres':
                postgres_secrets = get_postgres_credentials(
                    secret_name=config.POSTGRES_SECRETS_NAME,
                    region_name=config.AWS_REGION
                )
                
                # Override with environment variables if provided
                if config.DATABASE_HOST:
                    postgres_secrets['host'] = config.DATABASE_HOST
                if config.DATABASE_NAME:
                    postgres_secrets['database'] = config.DATABASE_NAME
                    
                configuration['postgres_connection_string'] = build_postgres_connection_string(postgres_secrets)
                logger.info("PostgreSQL configuration loaded successfully")
            
            logger.info("Configuration loaded from AWS Secrets Manager")
            return configuration
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get_last_collection_date(self) -> Optional[datetime]:
        """Get the date of the most recent data in the database
        
        Returns:
            The most recent date with data, or None if no data exists
        """
        try:
            # This method should be implemented in the storage classes
            # For now, we'll use a simple query approach
            if hasattr(self.storage, 'get_session'):
                with self.storage.get_session() as session:
                    # Query for the most recent date across key tables
                    from sqlalchemy import func
                    from database_models import Activity, Readiness, DailySleep
                    
                    max_activity = session.query(func.max(Activity.date)).scalar()
                    max_readiness = session.query(func.max(Readiness.date)).scalar()
                    max_sleep = session.query(func.max(DailySleep.date)).scalar()
                    
                    dates = [d for d in [max_activity, max_readiness, max_sleep] if d is not None]
                    if dates:
                        most_recent = max(dates)
                        logger.info(f"Most recent data found: {most_recent}")
                        return datetime.combine(most_recent, datetime.min.time())
            
            return None
        except Exception as e:
            logger.warning(f"Could not determine last collection date: {e}")
            return None
    
    def collect_data(self, days_back: Optional[int] = None, use_smart_backfill: bool = True) -> Dict[str, Any]:
        """Collect all data types for the specified period
        
        Args:
            days_back: Number of days to collect (None uses config default)
            use_smart_backfill: If True, only collect data since last collection
            
        Returns:
            Summary of collection results
        """
        collection_start_time = datetime.now()
        success = False
        error_msg = None
        
        try:
            end_date = datetime.now().date()
            
            # Determine start date based on smart backfill
            if use_smart_backfill and days_back is None:
                last_collection = self.get_last_collection_date()
                if last_collection:
                    # Add 1 day to avoid re-collecting the last day
                    start_date = (last_collection + timedelta(days=1)).date()
                    # But don't go further back than the configured backfill days
                    max_backfill_date = end_date - timedelta(days=self.config['days_to_backfill'])
                    if start_date < max_backfill_date:
                        start_date = max_backfill_date
                    logger.info(f"Smart backfill: collecting from {start_date} (last data: {last_collection.date()})")
                else:
                    # No existing data, use configured backfill
                    days_back = self.config['days_to_backfill']
                    start_date = end_date - timedelta(days=days_back)
                    logger.info(f"No existing data found, collecting last {days_back} days")
            else:
                # Manual days_back specified or smart backfill disabled
                if days_back is None:
                    days_back = self.config['days_to_backfill']
                start_date = end_date - timedelta(days=days_back)
            
            # Don't collect future data
            if start_date > end_date:
                logger.info("All data is up to date, nothing to collect")
                return {
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'collection_time': datetime.now().isoformat(),
                    'results': {'status': 'up_to_date'}
                }
            
            logger.info(f"Starting comprehensive data collection from {start_date} to {end_date}")
            
            summary = {
                'start_date': str(start_date),
                'end_date': str(end_date),
                'collection_time': datetime.now().isoformat(),
                'results': {}
            }
            
            # [Rest of the collection logic remains the same...]
            # Collect personal info first (not date-based)
            try:
                logger.info("Collecting personal info...")
                personal_info = self.oura_client.get_personal_info()
                
                # Save personal info
                count = self.storage.save_data([personal_info], 'personal_info')
                summary['results']['personal_info'] = {
                    'collected': True,
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect personal info: {e}")
                summary['results']['personal_info'] = {'error': str(e)}
            
            # Core data collection
            collected_data = {}
            
            # Sleep period data (detailed sleep stages)
            try:
                logger.info("Collecting sleep period data...")
                raw_sleep_periods = self.oura_client.get_sleep_periods(start_date, end_date)
                processed_sleep_periods = self.processor.process_sleep_periods(raw_sleep_periods)
                
                # Save processed data (raw data is included in the processed records)
                count = self.storage.save_data(processed_sleep_periods, 'sleep_periods')
                
                collected_data['sleep_periods'] = processed_sleep_periods
                summary['results']['sleep_periods'] = {
                    'records_collected': len(raw_sleep_periods),
                    'records_processed': len(processed_sleep_periods),
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect sleep period data: {e}")
                summary['results']['sleep_periods'] = {'error': str(e)}
            
            # Daily sleep scores
            try:
                logger.info("Collecting daily sleep scores...")
                raw_daily_sleep = self.oura_client.get_daily_sleep(start_date, end_date)
                processed_daily_sleep = self.processor.process_daily_sleep(raw_daily_sleep)
                
                # Save processed data
                count = self.storage.save_data(processed_daily_sleep, 'daily_sleep')
                
                collected_data['daily_sleep'] = processed_daily_sleep
                summary['results']['daily_sleep'] = {
                    'records_collected': len(raw_daily_sleep),
                    'records_processed': len(processed_daily_sleep),
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect daily sleep data: {e}")
                summary['results']['daily_sleep'] = {'error': str(e)}
            
            # Activity data
            try:
                logger.info("Collecting activity data...")
                raw_activity = self.oura_client.get_daily_activity(start_date, end_date)
                processed_activity = self.processor.process_activity_data(raw_activity)
                
                # Save processed data
                count = self.storage.save_data(processed_activity, 'activity')
                
                collected_data['activity'] = processed_activity
                summary['results']['activity'] = {
                    'records_collected': len(raw_activity),
                    'records_processed': len(processed_activity),
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect activity data: {e}")
                summary['results']['activity'] = {'error': str(e)}
            
            # Readiness data
            try:
                logger.info("Collecting readiness data...")
                raw_readiness = self.oura_client.get_daily_readiness(start_date, end_date)
                processed_readiness = self.processor.process_readiness_data(raw_readiness)
                
                # Save processed data
                count = self.storage.save_data(processed_readiness, 'readiness')
                
                collected_data['readiness'] = processed_readiness
                summary['results']['readiness'] = {
                    'records_collected': len(raw_readiness),
                    'records_processed': len(processed_readiness),
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect readiness data: {e}")
                summary['results']['readiness'] = {'error': str(e)}
            
            # Workout data
            try:
                logger.info("Collecting workout data...")
                raw_workouts = self.oura_client.get_workouts(start_date, end_date)
                processed_workouts = self.processor.process_workout_data(raw_workouts)
                
                # Save processed data
                count = self.storage.save_data(processed_workouts, 'workouts')
                
                collected_data['workouts'] = processed_workouts
                summary['results']['workouts'] = {
                    'records_collected': len(raw_workouts),
                    'records_processed': len(processed_workouts),
                    'records_saved': count
                }
                
            except Exception as e:
                logger.error(f"Failed to collect workout data: {e}")
                summary['results']['workouts'] = {'error': str(e)}
            
            # Stress data (if enabled)
            if self.config.get('collect_all_endpoints', True) or 'stress' in self.config.get('endpoints_to_collect', []):
                try:
                    logger.info("Collecting stress data...")
                    raw_stress = self.oura_client.get_daily_stress(start_date, end_date)
                    processed_stress = self.processor.process_stress_data(raw_stress)
                    
                    # Save processed data
                    count = self.storage.save_data(processed_stress, 'stress')
                    
                    collected_data['stress'] = processed_stress
                    summary['results']['stress'] = {
                        'records_collected': len(raw_stress),
                        'records_processed': len(processed_stress),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to collect stress data: {e}")
                    summary['results']['stress'] = {'error': str(e)}
            
            # Additional endpoints if enabled
            if self.config.get('collect_all_endpoints', True):
                # Heart rate time series
                try:
                    logger.info("Collecting heart rate data...")
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    end_datetime = datetime.combine(end_date, datetime.max.time())
                    
                    raw_heart_rate = self.oura_client.get_heart_rate(start_datetime, end_datetime)
                    
                    # Save heart rate data
                    count = self.storage.save_data(raw_heart_rate, 'heart_rate')
                    
                    summary['results']['heart_rate'] = {
                        'records_collected': len(raw_heart_rate),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to collect heart rate data: {e}")
                    summary['results']['heart_rate'] = {'error': str(e)}
                
                # SpO2 data
                try:
                    logger.info("Collecting SpO2 data...")
                    raw_spo2 = self.oura_client.get_daily_spo2(start_date, end_date)
                    
                    # Save raw data
                    count = self.storage.save_data(raw_spo2, 'spo2')
                    
                    summary['results']['spo2'] = {
                        'records_collected': len(raw_spo2),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to collect SpO2 data: {e}")
                    summary['results']['spo2'] = {'error': str(e)}
                
                # Sessions data
                try:
                    logger.info("Collecting sessions data...")
                    raw_sessions = self.oura_client.get_sessions(start_date, end_date)
                    
                    # Save raw data
                    count = self.storage.save_data(raw_sessions, 'sessions')
                    
                    summary['results']['sessions'] = {
                        'records_collected': len(raw_sessions),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to collect sessions data: {e}")
                    summary['results']['sessions'] = {'error': str(e)}
                
                # Tags data
                try:
                    logger.info("Collecting tags data...")
                    raw_tags = self.oura_client.get_enhanced_tags(start_date, end_date)
                    
                    # Save raw data
                    count = self.storage.save_data(raw_tags, 'tags')
                    
                    summary['results']['tags'] = {
                        'records_collected': len(raw_tags),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to collect tags data: {e}")
                    summary['results']['tags'] = {'error': str(e)}
            
            # Create comprehensive daily summaries
            if all(k in collected_data for k in ['sleep_periods', 'daily_sleep', 'activity', 'readiness']):
                try:
                    logger.info("Creating comprehensive daily summaries...")
                    daily_summaries = self.processor.create_daily_summary(
                        sleep_periods=collected_data['sleep_periods'],
                        daily_sleep=collected_data['daily_sleep'],
                        activity_data=collected_data['activity'],
                        readiness_data=collected_data['readiness'],
                        stress_data=collected_data.get('stress'),
                        workout_data=collected_data.get('workouts')
                    )
                    
                    count = self.storage.save_data(daily_summaries, 'daily_summaries')
                    summary['results']['daily_summaries'] = {
                        'records_created': len(daily_summaries),
                        'records_saved': count
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to create daily summaries: {e}")
                    summary['results']['daily_summaries'] = {'error': str(e)}
            
            # Save collection summary
            self.storage.save_collection_summary(summary)
            
            logger.info("Comprehensive data collection completed")
            success = True
            return summary
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Collection failed: {error_msg}")
            raise
        finally:
            # Update health status
            self.health_status.update_collection(success, error_msg)
    
    def run_once(self, days_back: Optional[int] = None):
        """Run collection once and exit
        
        Args:
            days_back: Number of days to collect
        """
        logger.info("Running single comprehensive collection")
        # For run_once, don't use smart backfill if days_back is specified
        use_smart = days_back is None
        summary = self.collect_data(days_back, use_smart_backfill=use_smart)
        
        # Log summary statistics
        total_records = 0
        successful_endpoints = 0
        failed_endpoints = 0
        
        for data_type, result in summary['results'].items():
            if 'error' in result:
                logger.error(f"{data_type}: {result['error']}")
                failed_endpoints += 1
            else:
                records = result.get('records_saved', 0) or result.get('records_created', 0)
                if records > 0:
                    successful_endpoints += 1
                    total_records += records
                logger.info(f"{data_type}: {records} records saved")
        
        logger.info(f"Collection summary: {total_records} total records saved from "
                   f"{successful_endpoints} endpoints (failed: {failed_endpoints})")
    
    def run_continuous(self):
        """Run continuous collection on schedule"""
        # Run initial collection with smart backfill
        self.collect_data(use_smart_backfill=True)
        
        # Schedule periodic collections with smart backfill
        interval = self.config['collection_interval']
        schedule.every(interval).seconds.do(lambda: self.collect_data(use_smart_backfill=True))
        
        logger.info(f"Starting continuous collection every {interval} seconds")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Stopping continuous collection")
                break
            except Exception as e:
                logger.error(f"Error in continuous collection: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def __del__(self):
        """Cleanup when collector is destroyed"""
        if hasattr(self, 'storage') and hasattr(self.storage, 'close'):
            self.storage.close()

def main():
    """Main entry point"""
    try:
        collector = OuraCollector()
        
        if config.RUN_ONCE:
            days = config.DAYS_TO_BACKFILL
            collector.run_once(days)
        else:
            collector.run_continuous()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
