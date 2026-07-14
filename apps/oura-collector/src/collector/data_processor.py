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
                    'score': record.get('score'),

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
                    'lowest_heart_rate': record.get('lowest_heart_rate'),

                    # Movement data
                    'movement_30_sec': record.get('movement_30_sec'),
                    'sleep_phase_5_min': record.get('sleep_phase_5_min'),

                    # New comprehensive fields (schema v2)
                    'period_number': record.get('period_number'),
                    'low_battery_alert': record.get('low_battery_alert'),
                    'sleep_score_delta': record.get('sleep_score_delta'),
                    'readiness_score_delta': record.get('readiness_score_delta'),
                    'sleep_algorithm_version': record.get('sleep_algorithm_version'),
                    'sleep_analysis_reason': record.get('sleep_analysis_reason'),
                    'ring_id': record.get('ring_id'),

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
                    'sedentary_met_minutes': record.get('sedentary_met_minutes'),

                    # Goals
                    'target_meters': record.get('target_meters'),
                    'meters_to_target': record.get('meters_to_target'),
                    'equivalent_walking_distance': record.get('equivalent_walking_distance'),

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
                    'score_sleep_regularity': contributors.get('sleep_regularity'),

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
                # Convert from seconds to minutes
                stress_seconds = record.get('stress_high', 0)
                recovery_seconds = record.get('recovery_high', 0)
                stress_minutes = round(stress_seconds / 60, 1) if stress_seconds else 0
                recovery_minutes = round(recovery_seconds / 60, 1) if recovery_seconds else 0
                
                processed_record = {
                    'date': record.get('day'),
                    'stress_high_minutes': stress_minutes,
                    'recovery_high_minutes': recovery_minutes,
                    'day_summary': record.get('day_summary'),
                    
                    # Calculate stress/recovery ratio
                    'stress_recovery_ratio': round(
                        stress_minutes / recovery_minutes,
                        2
                    ) if recovery_minutes > 0 else None,
                    
                    'raw_data': record
                }
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing stress record for {record.get('day')}: {e}")
                
        logger.info(f"Processed {len(processed)} stress records")
        return processed

    @staticmethod
    def process_session_data(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process session data (breathing, meditation, etc.)
        
        Args:
            raw_data: Raw session records from Oura API
            
        Returns:
            Processed session records with extracted time series
        """
        processed = []
        
        for record in raw_data:
            try:
                processed_record = {
                    'session_id': record.get('id'),
                    'date': record.get('day'),
                    'type': record.get('type'),  # breathing, meditation, etc.
                    'start_datetime': record.get('start_datetime'),
                    'end_datetime': record.get('end_datetime'),
                    'mood': record.get('mood'),
                    
                    # Extract time series data
                    'heart_rate_data': record.get('heart_rate', {}),
                    'hrv_data': record.get('heart_rate_variability', {}),
                    'motion_count_data': record.get('motion_count', {}),
                    
                    'raw_data': record
                }
                
                # Calculate duration if start and end times available
                if record.get('start_datetime') and record.get('end_datetime'):
                    start = datetime.fromisoformat(record['start_datetime'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(record['end_datetime'].replace('Z', '+00:00'))
                    processed_record['duration_minutes'] = round((end - start).total_seconds() / 60, 1)
                
                processed.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing session record: {e}")
                
        logger.info(f"Processed {len(processed)} session records")
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

    @staticmethod
    def create_daily_health_composite(daily_sleep: Dict[str, Any],
                                     activity: Dict[str, Any],
                                     readiness: Dict[str, Any],
                                     stress: Optional[Dict[str, Any]] = None,
                                     spo2: Optional[Dict[str, Any]] = None,
                                     vo2_max: Optional[Dict[str, Any]] = None,
                                     cardio_age: Optional[Dict[str, Any]] = None,
                                     resilience: Optional[Dict[str, Any]] = None,
                                     workouts: Optional[List[Dict[str, Any]]] = None,
                                     sessions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create comprehensive daily health composite with wellness assessment

        Args:
            daily_sleep: Daily sleep data
            activity: Daily activity data
            readiness: Daily readiness data
            stress: Daily stress data (optional)
            spo2: SpO2 data (optional)
            vo2_max: VO2 Max data (optional)
            cardio_age: Cardiovascular age data (optional)
            resilience: Resilience data (optional)
            workouts: Workout list (optional)
            sessions: Session list (optional)

        Returns:
            Comprehensive health composite for the day
        """
        date_str = daily_sleep.get('date') or activity.get('date') or readiness.get('date')

        sleep_score = daily_sleep.get('sleep_score', 0)
        activity_score = activity.get('activity_score', 0)
        readiness_score = readiness.get('readiness_score', 0)

        # Calculate overall health score (weighted average)
        overall_score = (sleep_score * 0.35 + activity_score * 0.35 + readiness_score * 0.30)

        # Determine wellness status
        if overall_score >= 80:
            wellness_status = 'excellent'
        elif overall_score >= 65:
            wellness_status = 'good'
        elif overall_score >= 50:
            wellness_status = 'fair'
        elif overall_score >= 35:
            wellness_status = 'poor'
        else:
            wellness_status = 'at_risk'

        # Aggregate workout data
        total_workouts = len(workouts) if workouts else 0
        total_workout_minutes = sum(w.get('duration_minutes', 0) for w in workouts) if workouts else 0
        workout_calories = sum(w.get('calories', 0) for w in workouts) if workouts else 0

        # Aggregate meditation data
        meditation_sessions = 0
        total_meditation_minutes = 0
        if sessions:
            for session in sessions:
                if session.get('type') in ['breathing', 'meditation']:
                    meditation_sessions += 1
                    duration = session.get('duration_minutes', 0)
                    total_meditation_minutes += duration if duration else 0

        # Risk factor analysis
        risk_factors = []
        if sleep_score < 60:
            risk_factors.append('poor_sleep')
        if activity_score < 50:
            risk_factors.append('low_activity')
        if readiness_score < 60:
            risk_factors.append('low_readiness')
        if stress and stress.get('stress_high_minutes', 0) > 240:  # More than 4 hours
            risk_factors.append('high_stress')
        if spo2 and spo2.get('spo2_percentage_avg', 100) < 95:
            risk_factors.append('low_spo2')

        # Generate recommendations
        recommendations = []
        if sleep_score < 70:
            recommendations.append('Prioritize sleep: aim for 7-9 hours tonight')
        if activity_score < 60:
            recommendations.append('Increase daily activity: target 10,000 steps')
        if stress and stress.get('stress_high_minutes', 0) > 180:
            recommendations.append('Practice stress management: try meditation or breathing exercises')
        if readiness_score < 70:
            recommendations.append('Consider a recovery day: reduce intense exercise')

        # Calculate parasympathetic balance (HRV-based, normalized 0-1)
        hrv_index = readiness.get('hrv_balance', 0)
        parasympathetic_balance = min(1.0, max(0.0, (hrv_index or 0) / 100))

        # Determine stress level
        stress_minutes = stress.get('stress_high_minutes', 0) if stress else 0
        if stress_minutes > 240:
            stress_level = 'high'
        elif stress_minutes > 120:
            stress_level = 'elevated'
        elif stress_minutes > 60:
            stress_level = 'moderate'
        else:
            stress_level = 'low'

        # Determine recovery status
        if readiness_score >= 75 and sleep_score >= 70:
            recovery_status = 'optimal'
        elif readiness_score >= 60 and sleep_score >= 60:
            recovery_status = 'good'
        elif readiness_score >= 50 or sleep_score >= 50:
            recovery_status = 'adequate'
        else:
            recovery_status = 'compromised'

        composite = {
            'date': date_str,

            # Overall assessment
            'overall_health_score': round(overall_score, 1),
            'wellness_status': wellness_status,

            # Sleep metrics
            'sleep_score': sleep_score,
            'sleep_duration_hours': round(daily_sleep.get('total_sleep_duration_secs', 0) / 3600, 1),
            'sleep_quality_indicator': 'excellent' if sleep_score >= 80 else ('good' if sleep_score >= 65 else ('fair' if sleep_score >= 50 else 'poor')),
            'deep_sleep_percentage': daily_sleep.get('score_deep_sleep', 0),
            'rem_sleep_percentage': daily_sleep.get('score_rem_sleep', 0),

            # Activity metrics
            'activity_score': activity_score,
            'activity_status': 'exceeding' if activity_score >= 90 else ('meeting' if activity_score >= 70 else 'below_target'),
            'total_active_minutes': activity.get('high_activity_minutes', 0) + activity.get('medium_activity_minutes', 0),
            'steps': activity.get('steps', 0),
            'met_minutes': activity.get('met_minutes', 0),

            # Recovery & readiness
            'readiness_score': readiness_score,
            'recovery_status': recovery_status,
            'resting_heart_rate': readiness.get('resting_heart_rate'),
            'hrv_index': hrv_index,

            # Stress & nervous system
            'stress_level': stress_level,
            'recovery_index': stress.get('recovery_high_minutes', 0) if stress else 0,
            'parasympathetic_balance': round(parasympathetic_balance, 2),

            # Respiratory & cardiovascular
            'spo2_status': 'normal' if (spo2.get('spo2_percentage_avg', 100) >= 95 if spo2 else True) else 'watch',
            'spo2_average': spo2.get('spo2_percentage_avg') if spo2 else None,
            'spo2_lowest': spo2.get('lowest_spo2') if spo2 else None,
            'vo2_max': vo2_max.get('vo2_max') if vo2_max else None,
            'cardiovascular_age': cardio_age.get('cardiovascular_age') if cardio_age else None,

            # Behavioral
            'meditation_sessions': meditation_sessions,
            'total_meditation_minutes': int(total_meditation_minutes),
            'workout_sessions': total_workouts,
            'workout_minutes': int(total_workout_minutes),
            'workout_calories': int(workout_calories),

            # Resilience
            'resilience_level': resilience.get('resilience_level') if resilience else None,

            # Analysis
            'risk_factors': risk_factors,
            'wellness_trends': [],
            'recommendations': recommendations,
            'alerts': [f'High stress level detected' if stress_level in ['high', 'elevated'] else None,
                      f'Low sleep quality' if sleep_score < 60 else None,
                      f'Low SpO2' if spo2 and spo2.get('spo2_percentage_avg', 100) < 95 else None],
            'alerts': [a for a in [
                'High stress level detected' if stress_level in ['high', 'elevated'] else None,
                'Low sleep quality' if sleep_score < 60 else None,
                'Low SpO2' if spo2 and spo2.get('spo2_percentage_avg', 100) < 95 else None,
                'Low activity level' if activity_score < 50 else None,
                'Poor recovery' if recovery_status == 'compromised' else None,
            ] if a],

            'raw_data': {
                'sleep': daily_sleep,
                'activity': activity,
                'readiness': readiness,
                'stress': stress,
                'spo2': spo2,
            }
        }

        return composite

    @staticmethod
    def process_sleep_phase_timeseries(sleep_period_id: str,
                                      bedtime_start: str,
                                      sleep_phase_5_min: Optional[str] = None,
                                      sleep_phase_30_sec: Optional[str] = None,
                                      movement_30_sec: Optional[str] = None) -> List[Dict[str, Any]]:
        """Process sleep phase time-series data (5-min and 30-sec granularity)

        Args:
            sleep_period_id: ID of the sleep period
            bedtime_start: Start time of sleep period
            sleep_phase_5_min: Encoded sleep phases for each 5-minute interval
            sleep_phase_30_sec: Encoded sleep phases for each 30-second interval
            movement_30_sec: Encoded movement data for each 30-second interval

        Returns:
            List of time-series records for storage
        """
        timeseries = []

        try:
            if not bedtime_start:
                return []

            bedtime_dt = datetime.fromisoformat(bedtime_start.replace('Z', '+00:00'))

            # Process 30-second data (highest granularity)
            if sleep_phase_30_sec or movement_30_sec:
                # These are typically encoded strings; store as-is for decoding later
                ts_record = {
                    'sleep_period_id': sleep_period_id,
                    'timestamp': bedtime_dt.isoformat(),
                    'sleep_phase_5_min': sleep_phase_5_min,
                    'sleep_phase_30_sec': sleep_phase_30_sec,
                    'movement_30_sec': movement_30_sec,
                }
                timeseries.append(ts_record)

        except Exception as e:
            logger.error(f"Error processing sleep phase timeseries for period {sleep_period_id}: {e}")

        return timeseries

    @staticmethod
    def process_activity_met_timeseries(activity_date: str,
                                       met_data: Optional[Dict[str, Any]] = None,
                                       class_5_min: Optional[str] = None) -> Dict[str, Any]:
        """Process activity MET time-series and 5-minute activity class data

        Args:
            activity_date: Date of the activity
            met_data: MET time-series dict with interval, items, timestamp
            class_5_min: Encoded activity class for each 5-minute interval

        Returns:
            Time-series record for storage
        """
        if not met_data and not class_5_min:
            return {}

        ts_record = {
            'activity_date': activity_date,
            'class_5_min': class_5_min,
            'met_interval': met_data.get('interval') if met_data else None,
            'met_items': met_data.get('items') if met_data else None,
            'met_timestamp': met_data.get('timestamp') if met_data else None,
        }

        return ts_record
