"""Data processing and transformation utilities"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and transform Oura data"""
    
    @staticmethod
    def process_sleep_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw sleep data
        
        Args:
            raw_data: Raw sleep records from Oura API
            
        Returns:
            Processed sleep records with additional fields
        """
        processed = []
        
        for record in raw_data:
            try:
                # Calculate additional metrics
                total_sleep = record.get('total', 0)
                time_in_bed = record.get('duration', 0)
                efficiency = (total_sleep / time_in_bed * 100) if time_in_bed > 0 else 0
                
                processed_record = {
                    'date': record.get('day'),
                    'score': record.get('score'),
                    'total_sleep_hours': round(total_sleep / 3600, 2) if total_sleep else 0,
                    'rem_hours': round(record.get('rem', 0) / 3600, 2),
                    'deep_hours': round(record.get('deep', 0) / 3600, 2),
                    'light_hours': round(record.get('light', 0) / 3600, 2),
                    'awake_hours': round(record.get('awake', 0) / 3600, 2),
                    'efficiency_percent': round(efficiency, 1),
                    'heart_rate_avg': record.get('average_heart_rate'),
                    'hrv_avg': record.get('average_hrv'),
                    'temperature_deviation': record.get('temperature_deviation'),
                    'respiratory_rate': record.get('average_breath'),
                    'bedtime_start': record.get('bedtime_start'),
                    'bedtime_end': record.get('bedtime_end'),
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing sleep record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} sleep records")
        return processed
    
    @staticmethod
    def process_activity_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw activity data
        
        Args:
            raw_data: Raw activity records from Oura API
            
        Returns:
            Processed activity records with additional fields
        """
        processed = []
        
        for record in raw_data:
            try:
                # Convert meters to kilometers
                distance_km = record.get('equivalent_walking_distance', 0) / 1000
                
                # Convert activity times from seconds to minutes
                high_minutes = record.get('high_activity_time', 0) / 60
                medium_minutes = record.get('medium_activity_time', 0) / 60
                low_minutes = record.get('low_activity_time', 0) / 60
                sedentary_minutes = record.get('sedentary_time', 0) / 60
                
                processed_record = {
                    'date': record.get('day'),
                    'score': record.get('score'),
                    'steps': record.get('steps'),
                    'distance_km': round(distance_km, 2),
                    'calories_active': record.get('active_calories'),
                    'calories_total': record.get('total_calories'),
                    'high_activity_minutes': round(high_minutes, 1),
                    'medium_activity_minutes': round(medium_minutes, 1),
                    'low_activity_minutes': round(low_minutes, 1),
                    'sedentary_minutes': round(sedentary_minutes, 1),
                    'met_minutes': record.get('met_minutes'),
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing activity record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} activity records")
        return processed
    
    @staticmethod
    def process_readiness_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw readiness data
        
        Args:
            raw_data: Raw readiness records from Oura API
            
        Returns:
            Processed readiness records with additional fields
        """
        processed = []
        
        for record in raw_data:
            try:
                processed_record = {
                    'date': record.get('day'),
                    'score': record.get('score'),
                    'temperature_deviation': record.get('temperature_deviation'),
                    'hrv_balance': record.get('hrv_balance'),
                    'recovery_index': record.get('recovery_index'),
                    'resting_heart_rate': record.get('resting_heart_rate'),
                    'contributors': record.get('contributors', {}),
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing readiness record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} readiness records")
        return processed
    
    @staticmethod
    def create_daily_summary(sleep_data: List[Dict], 
                           activity_data: List[Dict], 
                           readiness_data: List[Dict]) -> List[Dict[str, Any]]:
        """Create daily summary combining all data types
        
        Args:
            sleep_data: Processed sleep records
            activity_data: Processed activity records
            readiness_data: Processed readiness records
            
        Returns:
            List of daily summaries
        """
        # Create lookup dictionaries by date
        sleep_by_date = {record['date']: record for record in sleep_data}
        activity_by_date = {record['date']: record for record in activity_data}
        readiness_by_date = {record['date']: record for record in readiness_data}
        
        # Get all unique dates
        all_dates = set()
        all_dates.update(sleep_by_date.keys())
        all_dates.update(activity_by_date.keys())
        all_dates.update(readiness_by_date.keys())
        
        summaries = []
        for date in sorted(all_dates):
            summary = {
                'date': date,
                'sleep': sleep_by_date.get(date, {}),
                'activity': activity_by_date.get(date, {}),
                'readiness': readiness_by_date.get(date, {}),
                'overall_health_score': None
            }
            
            # Calculate overall health score (simple average)
            scores = []
            if summary['sleep'].get('score'):
                scores.append(summary['sleep']['score'])
            if summary['activity'].get('score'):
                scores.append(summary['activity']['score'])
            if summary['readiness'].get('score'):
                scores.append(summary['readiness']['score'])
                
            if scores:
                summary['overall_health_score'] = round(sum(scores) / len(scores), 1)
            
            summaries.append(summary)
        
        logger.info(f"Created {len(summaries)} daily summaries")
        return summaries