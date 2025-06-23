"""Enhanced data processing and transformation utilities for Oura data"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import statistics

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and transform Oura data with enhanced metrics"""
    
    @staticmethod
    def process_sleep_periods(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw sleep period data with detailed metrics
        
        Args:
            raw_data: Raw sleep period records from Oura API
            
        Returns:
            Processed sleep records with additional fields
        """
        processed = []
        
        for record in raw_data:
            try:
                # Calculate sleep metrics
                total_sleep = record.get('total_sleep_duration') or 0
                time_in_bed = record.get('time_in_bed', 0)
                efficiency = record.get('efficiency', 0)
                
                # Calculate sleep stage percentages
                rem_duration = record.get('rem_sleep_duration', 0)
                deep_duration = record.get('deep_sleep_duration', 0)
                light_duration = record.get('light_sleep_duration', 0)
                
                total_sleep_stages = rem_duration + deep_duration + light_duration
                
                processed_record = {
                    'date': record.get('day'),
                    'period_id': record.get('id'),
                    'type': record.get('type', 'long_sleep'),
                    'score': record.get('sleep_score_delta'),
                    
                    # Time metrics
                    'bedtime_start': record.get('bedtime_start'),
                    'bedtime_end': record.get('bedtime_end'),
                    'total_sleep_hours': round(total_sleep / 3600, 2) if total_sleep else 0,
                    'time_in_bed_hours': round(time_in_bed / 3600, 2) if time_in_bed else 0,
                    
                    # Sleep stages
                    'rem_hours': round(rem_duration / 3600, 2),
                    'deep_hours': round(deep_duration / 3600, 2),
                    'light_hours': round(light_duration / 3600, 2),
                    'awake_time': round(record.get('awake_time', 0) / 3600, 2),
                    
                    # Sleep stage percentages
                    'rem_percentage': round((rem_duration / total_sleep_stages * 100), 1) if total_sleep_stages > 0 else 0,
                    'deep_percentage': round((deep_duration / total_sleep_stages * 100), 1) if total_sleep_stages > 0 else 0,
                    'light_percentage': round((light_duration / total_sleep_stages * 100), 1) if total_sleep_stages > 0 else 0,
                    
                    # Efficiency and quality
                    'efficiency_percent': efficiency,
                    'latency_minutes': round(record.get('latency', 0) / 60, 1),
                    'restless_periods': record.get('restless_periods', 0),
                    
                    # Physiological metrics
                    'heart_rate_avg': record.get('average_heart_rate'),
                    'heart_rate_min': record.get('lowest_heart_rate'),
                    'hrv_avg': record.get('average_hrv'),
                    'respiratory_rate': record.get('average_breath'),
                    
                    # Movement data
                    'movement_30_sec': record.get('movement_30_sec'),
                    'sleep_phase_5_min': record.get('sleep_phase_5_min'),
                    
                    # Time series data references
                    'has_heart_rate_data': bool(record.get('heart_rate')),
                    'has_hrv_data': bool(record.get('hrv')),
                    
                    'raw_data': record
                }
                
                # Add HRV insights if available
                if record.get('hrv') and record['hrv'].get('items'):
                    hrv_values = [v for v in record['hrv']['items'] if v is not None]
                    if hrv_values:
                        processed_record['hrv_max'] = max(hrv_values)
                        processed_record['hrv_min'] = min(hrv_values)
                        processed_record['hrv_stdev'] = round(statistics.stdev(hrv_values), 1) if len(hrv_values) > 1 else 0
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing sleep period for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} sleep period records")
        return processed
    
    @staticmethod
    def process_daily_sleep(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process daily sleep score data
        
        Args:
            raw_data: Raw daily sleep records from Oura API
            
        Returns:
            Processed daily sleep records
        """
        processed = []
        
        for record in raw_data:
            try:
                contributors = record.get('contributors', {})
                
                processed_record = {
                    'date': record.get('day'),
                    'sleep_score': record.get('score'),
                    'timestamp': record.get('timestamp'),
                    
                    # Contributors
                    'score_deep_sleep': contributors.get('deep_sleep'),
                    'score_efficiency': contributors.get('efficiency'),
                    'score_latency': contributors.get('latency'),
                    'score_rem_sleep': contributors.get('rem_sleep'),
                    'score_restfulness': contributors.get('restfulness'),
                    'score_timing': contributors.get('timing'),
                    'score_total_sleep': contributors.get('total_sleep'),
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing daily sleep for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} daily sleep records")
        return processed
    
    @staticmethod
    def process_activity_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw activity data with enhanced metrics
        
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
                non_wear_minutes = record.get('non_wear_time', 0) / 60
                
                # Calculate total active time
                total_active_minutes = high_minutes + medium_minutes + low_minutes
                
                # Get contributor scores
                contributors = record.get('contributors', {})
                
                processed_record = {
                    'date': record.get('day'),
                    'activity_score': record.get('score'),
                    'steps': record.get('steps'),
                    'distance_km': round(distance_km, 2),
                    
                    # Calories
                    'calories_active': record.get('active_calories'),
                    'calories_total': record.get('total_calories'),
                    'calories_target': record.get('target_calories'),
                    
                    # Activity time breakdown
                    'high_activity_minutes': round(high_minutes, 1),
                    'medium_activity_minutes': round(medium_minutes, 1),
                    'low_activity_minutes': round(low_minutes, 1),
                    'sedentary_minutes': round(sedentary_minutes, 1),
                    'non_wear_minutes': round(non_wear_minutes, 1),
                    'total_active_minutes': round(total_active_minutes, 1),
                    
                    # MET metrics
                    'met_minutes': record.get('met_minutes'),
                    'average_met': record.get('average_met_minutes'),
                    'high_activity_met_minutes': record.get('high_activity_met_minutes'),
                    'medium_activity_met_minutes': record.get('medium_activity_met_minutes'),
                    'low_activity_met_minutes': record.get('low_activity_met_minutes'),
                    
                    # Goals
                    'target_meters': record.get('target_meters'),
                    'meters_to_target': record.get('meters_to_target'),
                    
                    # Other metrics
                    'inactivity_alerts': record.get('inactivity_alerts', 0),
                    'resting_time_minutes': round(record.get('resting_time', 0) / 60, 1),
                    
                    # Contributor scores
                    'score_meet_daily_targets': contributors.get('meet_daily_targets'),
                    'score_move_every_hour': contributors.get('move_every_hour'),
                    'score_recovery_time': contributors.get('recovery_time'),
                    'score_stay_active': contributors.get('stay_active'),
                    'score_training_frequency': contributors.get('training_frequency'),
                    'score_training_volume': contributors.get('training_volume'),
                    
                    # Time series reference
                    'has_met_data': bool(record.get('met')),
                    'class_5_min': record.get('class_5_min'),
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing activity record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} activity records")
        return processed
    
    @staticmethod
    def process_readiness_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw readiness data with enhanced metrics
        
        Args:
            raw_data: Raw readiness records from Oura API
            
        Returns:
            Processed readiness records with additional fields
        """
        processed = []
        
        for record in raw_data:
            try:
                contributors = record.get('contributors', {})
                
                processed_record = {
                    'date': record.get('day'),
                    'readiness_score': record.get('score'),
                    
                    # Temperature metrics
                    'temperature_deviation': record.get('temperature_deviation'),
                    'temperature_trend_deviation': record.get('temperature_trend_deviation'),
                    
                    # Recovery metrics
                    'recovery_index': record.get('recovery_index'),
                    'resting_heart_rate': record.get('resting_heart_rate'),
                    'hrv_balance': record.get('hrv_balance'),
                    
                    # Contributor scores
                    'score_activity_balance': contributors.get('activity_balance'),
                    'score_body_temperature': contributors.get('body_temperature'),
                    'score_hrv_balance': contributors.get('hrv_balance'),
                    'score_previous_day_activity': contributors.get('previous_day_activity'),
                    'score_previous_night': contributors.get('previous_night'),
                    'score_recovery_index': contributors.get('recovery_index'),
                    'score_resting_heart_rate': contributors.get('resting_heart_rate'),
                    'score_sleep_balance': contributors.get('sleep_balance'),
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing readiness record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} readiness records")
        return processed
    
    @staticmethod
    def process_workout_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process workout data
        
        Args:
            raw_data: Raw workout records from Oura API
            
        Returns:
            Processed workout records
        """
        processed = []
        
        for record in raw_data:
            try:
                # Calculate duration in minutes
                start_time = datetime.fromisoformat(record.get('start_datetime', '').replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(record.get('end_datetime', '').replace('Z', '+00:00'))
                duration_minutes = (end_time - start_time).total_seconds() / 60
                
                processed_record = {
                    'date': record.get('day'),
                    'workout_id': record.get('id'),
                    'activity': record.get('activity'),
                    'intensity': record.get('intensity'),
                    'label': record.get('label'),
                    'source': record.get('source'),
                    
                    # Time metrics
                    'start_datetime': record.get('start_datetime'),
                    'end_datetime': record.get('end_datetime'),
                    'duration_minutes': round(duration_minutes, 1),
                    
                    # Performance metrics
                    'calories': record.get('calories'),
                    'distance_meters': record.get('distance'),
                    'distance_km': round(record.get('distance', 0) / 1000, 2) if record.get('distance') else None,
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing workout record: {e}")
                
        logger.info(f"Processed {len(processed)} workout records")
        return processed
    
    @staticmethod
    def process_stress_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process daily stress data
        
        Args:
            raw_data: Raw stress records from Oura API
            
        Returns:
            Processed stress records
        """
        processed = []
        
        for record in raw_data:
            try:
                processed_record = {
                    'date': record.get('day'),
                    'stress_high_minutes': record.get('stress_high', 0),
                    'recovery_high_minutes': record.get('recovery_high', 0),
                    'day_summary': record.get('day_summary'),
                    
                    # Calculate stress/recovery ratio
                    'stress_recovery_ratio': round(
                        record.get('stress_high', 0) / record.get('recovery_high', 1),
                        2
                    ) if record.get('recovery_high', 0) > 0 else None,
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing stress record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} stress records")
        return processed
    
    @staticmethod
    def create_daily_summary(sleep_periods: List[Dict],
                           daily_sleep: List[Dict],
                           activity_data: List[Dict], 
                           readiness_data: List[Dict],
                           stress_data: Optional[List[Dict]] = None,
                           workout_data: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """Create enhanced daily summary combining all data types
        
        Args:
            sleep_periods: Processed sleep period records
            daily_sleep: Processed daily sleep score records
            activity_data: Processed activity records
            readiness_data: Processed readiness records
            stress_data: Optional processed stress records
            workout_data: Optional processed workout records
            
        Returns:
            List of comprehensive daily summaries
        """
        # Create lookup dictionaries by date
        sleep_periods_by_date = {}
        for record in sleep_periods:
            date = record['date']
            if date not in sleep_periods_by_date:
                sleep_periods_by_date[date] = []
            sleep_periods_by_date[date].append(record)
        
        daily_sleep_by_date = {record['date']: record for record in daily_sleep}
        activity_by_date = {record['date']: record for record in activity_data}
        readiness_by_date = {record['date']: record for record in readiness_data}
        
        stress_by_date = {}
        if stress_data:
            stress_by_date = {record['date']: record for record in stress_data}
        
        workouts_by_date = {}
        if workout_data:
            for workout in workout_data:
                date = workout['date']
                if date not in workouts_by_date:
                    workouts_by_date[date] = []
                workouts_by_date[date].append(workout)
        
        # Get all unique dates
        all_dates = set()
        all_dates.update(sleep_periods_by_date.keys())
        all_dates.update(daily_sleep_by_date.keys())
        all_dates.update(activity_by_date.keys())
        all_dates.update(readiness_by_date.keys())
        all_dates.update(stress_by_date.keys())
        all_dates.update(workouts_by_date.keys())
        
        summaries = []
        for date in sorted(all_dates):
            # Get primary sleep period (longest one)
            sleep_periods_for_date = sleep_periods_by_date.get(date, [])
            primary_sleep = None
            if sleep_periods_for_date:
                primary_sleep = max(sleep_periods_for_date, 
                                  key=lambda x: x.get('total_sleep_hours', 0))
            
            summary = {
                'date': date,
                'sleep_periods': sleep_periods_for_date,
                'primary_sleep': primary_sleep,
                'daily_sleep_score': daily_sleep_by_date.get(date, {}),
                'activity': activity_by_date.get(date, {}),
                'readiness': readiness_by_date.get(date, {}),
                'stress': stress_by_date.get(date, {}),
                'workouts': workouts_by_date.get(date, []),
                
                # Summary metrics
                'total_sleep_periods': len(sleep_periods_for_date),
                'total_workouts': len(workouts_by_date.get(date, [])),
                'overall_health_score': None,
                
                # Daily insights
                'insights': {}
            }
            
            # Calculate overall health score (weighted average)
            scores = []
            weights = []
            
            if summary['daily_sleep_score'].get('sleep_score'):
                scores.append(summary['daily_sleep_score']['sleep_score'])
                weights.append(0.4)  # Sleep is 40% of overall health
                
            if summary['activity'].get('activity_score'):
                scores.append(summary['activity']['activity_score'])
                weights.append(0.3)  # Activity is 30%
                
            if summary['readiness'].get('readiness_score'):
                scores.append(summary['readiness']['readiness_score'])
                weights.append(0.3)  # Readiness is 30%
                
            if scores and weights:
                weighted_sum = sum(s * w for s, w in zip(scores, weights))
                total_weight = sum(weights)
                summary['overall_health_score'] = round(weighted_sum / total_weight, 1)
            
            # Add insights
            insights = summary['insights']
            
            # Sleep insights
            if primary_sleep:
                if primary_sleep.get('efficiency_percent', 0) < 85:
                    insights['sleep_efficiency'] = 'Below optimal (< 85%)'
                if primary_sleep.get('deep_percentage', 0) < 15:
                    insights['deep_sleep'] = 'Low deep sleep percentage'
                if primary_sleep.get('hrv_avg'):
                    insights['hrv_trend'] = f"Average HRV: {primary_sleep['hrv_avg']}"
            
            # Activity insights  
            if summary['activity']:
                steps = summary['activity'].get('steps', 0)
                if steps < 8000:
                    insights['activity_level'] = f'Low step count: {steps}'
                elif steps > 15000:
                    insights['activity_level'] = f'High step count: {steps}'
            
            # Stress insights
            if summary['stress'] and summary['stress'].get('day_summary'):
                insights['stress_summary'] = summary['stress']['day_summary']
            
            summaries.append(summary)
        
        logger.info(f"Created {len(summaries)} daily summaries")
        return summaries