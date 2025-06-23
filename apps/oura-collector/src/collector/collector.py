#!/usr/bin/env python3
"""Main collector script that orchestrates data collection"""
import sys
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Import configuration
import config

# Import modules
from aws_secrets import AWSSecretsManager
from oura_client import OuraAPIClient
from data_processor import DataProcessor
from storage import DataStorage

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class OuraCollector:
    """Main collector class that orchestrates data collection"""
    
    def __init__(self):
        """Initialize the collector"""
        logger.info("Initializing Oura Collector")
        
        # Load configuration from AWS Secrets Manager
        self.config = self._load_configuration()
        
        # Initialize components
        self.oura_client = OuraAPIClient(self.config['oura_token'])
        self.processor = DataProcessor()
        self.storage = DataStorage(
            data_dir=config.DATA_DIR,
            output_format=config.OUTPUT_FORMAT
        )
        
        # Test connection
        if not self.oura_client.test_connection():
            raise RuntimeError("Failed to connect to Oura API")
        
        logger.info("Oura Collector initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from AWS Secrets Manager
        
        Returns:
            Configuration dictionary
        """
        secrets_manager = AWSSecretsManager(region=config.AWS_REGION)
        
        try:
            secrets = secrets_manager.get_secret(config.SECRETS_NAME)
            
            # Required configuration
            if 'oura_personal_access_token' not in secrets:
                raise ValueError("oura_personal_access_token not found in secrets")
            
            configuration = {
                'oura_token': secrets['oura_personal_access_token'],
                'collection_interval': secrets.get('collection_interval', config.COLLECTION_INTERVAL),
                'days_to_backfill': secrets.get('days_to_backfill', config.DAYS_TO_BACKFILL)
            }
            
            logger.info("Configuration loaded from AWS Secrets Manager")
            return configuration
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def collect_data(self, days_back: Optional[int] = None) -> Dict[str, Any]:
        """Collect all data types for the specified period
        
        Args:
            days_back: Number of days to collect (None uses config default)
            
        Returns:
            Summary of collection results
        """
        if days_back is None:
            days_back = self.config['days_to_backfill']
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Starting data collection from {start_date} to {end_date}")
        
        summary = {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'collection_time': datetime.now().isoformat(),
            'results': {}
        }
        
        # Collect sleep data
        try:
            logger.info("Collecting sleep data...")
            raw_sleep = self.oura_client.get_sleep_data(start_date, end_date)
            processed_sleep = self.processor.process_sleep_data(raw_sleep)
            
            # Save raw and processed data
            raw_path = self.storage.save_data(raw_sleep, 'sleep', raw=True)
            processed_path = self.storage.save_data(processed_sleep, 'sleep')
            
            summary['results']['sleep'] = {
                'records_collected': len(raw_sleep),
                'records_processed': len(processed_sleep),
                'raw_file': raw_path,
                'processed_file': processed_path
            }
            
        except Exception as e:
            logger.error(f"Failed to collect sleep data: {e}")
            summary['results']['sleep'] = {'error': str(e)}
        
        # Collect activity data
        try:
            logger.info("Collecting activity data...")
            raw_activity = self.oura_client.get_activity_data(start_date, end_date)
            processed_activity = self.processor.process_activity_data(raw_activity)
            
            # Save raw and processed data
            raw_path = self.storage.save_data(raw_activity, 'activity', raw=True)
            processed_path = self.storage.save_data(processed_activity, 'activity')
            
            summary['results']['activity'] = {
                'records_collected': len(raw_activity),
                'records_processed': len(processed_activity),
                'raw_file': raw_path,
                'processed_file': processed_path
            }
            
        except Exception as e:
            logger.error(f"Failed to collect activity data: {e}")
            summary['results']['activity'] = {'error': str(e)}
        
        # Collect readiness data
        try:
            logger.info("Collecting readiness data...")
            raw_readiness = self.oura_client.get_readiness_data(start_date, end_date)
            processed_readiness = self.processor.process_readiness_data(raw_readiness)
            
            # Save raw and processed data
            raw_path = self.storage.save_data(raw_readiness, 'readiness', raw=True)
            processed_path = self.storage.save_data(processed_readiness, 'readiness')
            
            summary['results']['readiness'] = {
                'records_collected': len(raw_readiness),
                'records_processed': len(processed_readiness),
                'raw_file': raw_path,
                'processed_file': processed_path
            }
            
        except Exception as e:
            logger.error(f"Failed to collect readiness data: {e}")
            summary['results']['readiness'] = {'error': str(e)}
        
        # Create daily summaries if we have all data types
        if all(k in locals() for k in ['processed_sleep', 'processed_activity', 'processed_readiness']):
            try:
                logger.info("Creating daily summaries...")
                daily_summaries = self.processor.create_daily_summary(
                    processed_sleep, processed_activity, processed_readiness
                )
                
                summary_path = self.storage.save_data(daily_summaries, 'daily_summaries')
                summary['results']['daily_summaries'] = {
                    'records_created': len(daily_summaries),
                    'file': summary_path
                }
                
            except Exception as e:
                logger.error(f"Failed to create daily summaries: {e}")
                summary['results']['daily_summaries'] = {'error': str(e)}
        
        # Save collection summary
        self.storage.save_collection_summary(summary)
        
        logger.info("Data collection completed")
        return summary
    
    def run_once(self, days_back: Optional[int] = None):
        """Run collection once and exit
        
        Args:
            days_back: Number of days to collect
        """
        logger.info("Running single collection")
        summary = self.collect_data(days_back)
        
        # Log summary statistics
        for data_type, result in summary['results'].items():
            if 'error' in result:
                logger.error(f"{data_type}: {result['error']}")
            else:
                logger.info(f"{data_type}: {result.get('records_collected', 0)} collected, "
                          f"{result.get('records_processed', 0)} processed")
    
    def run_continuous(self):
        """Run continuous collection on schedule"""
        # Run initial collection
        self.collect_data()
        
        # Schedule periodic collections
        interval = self.config['collection_interval']
        schedule.every(interval).seconds.do(self.collect_data)
        
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