"""PostgreSQL storage handler for Oura data"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, OperationalError

from database_models import (
    Base, PersonalInfo, SleepPeriod, DailySleep, Activity, 
    Readiness, Workout, Stress, HeartRate, DailySummary, CollectionLog,
    Session, VO2Max, CardiovascularAge, Resilience, SpO2, Tag, 
    SleepTime, RestModePeriod, RingConfiguration
)

logger = logging.getLogger(__name__)

class PostgresStorage:
    """Handle data storage to PostgreSQL database"""
    
    def __init__(self, connection_string: str):
        """Initialize PostgreSQL storage handler
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._ensure_tables()
        
    def _ensure_tables(self):
        """Ensure all required tables exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Provide a transactional scope for database operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_data(self, data: List[Dict[str, Any]], data_type: str, 
                  raw: bool = False) -> int:
        """Save data to PostgreSQL
        
        Args:
            data: Data to save
            data_type: Type of data (sleep_periods, activity, readiness, etc.)
            raw: Whether this is raw or processed data (raw data handled via JSON fields)
            
        Returns:
            Number of records saved
        """
        if not data:
            logger.warning(f"No data to save for {data_type}")
            return 0
        
        # Map data types to save methods
        save_methods = {
            'personal_info': self._save_personal_info,
            'sleep_periods': self._save_sleep_periods,
            'daily_sleep': self._save_daily_sleep,
            'activity': self._save_activity,
            'readiness': self._save_readiness,
            'workouts': self._save_workouts,
            'stress': self._save_stress,
            'heart_rate': self._save_heart_rate,
            'daily_summaries': self._save_daily_summaries,
            'spo2': self._save_spo2,
            'sessions': self._save_sessions,
            'tags': self._save_tags,
            'ring_configuration': self._save_ring_configuration,
            'sleep_time': self._save_sleep_time,
            'rest_mode_periods': self._save_rest_mode_periods,
            'vo2_max': self._save_vo2_max,
            'cardiovascular_age': self._save_cardiovascular_age,
            'resilience': self._save_resilience_data
        }
        
        save_method = save_methods.get(data_type)
        if not save_method:
            logger.warning(f"Unknown data type: {data_type}")
            return 0
        
        try:
            return save_method(data, data_type)
        except Exception as e:
            logger.error(f"Failed to save {data_type} data: {e}")
            raise
    
    def _save_personal_info(self, data: List[Dict], data_type: str) -> int:
        """Save personal info data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(PersonalInfo).values(
                        user_id=record.get('id', 'unknown'),
                        age=record.get('age'),
                        weight=record.get('weight'),
                        height=record.get('height'),
                        biological_sex=record.get('biological_sex'),
                        email=record.get('email'),
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['user_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving personal info: {e}")
            
            logger.info(f"Saved {count} personal info records")
            return count
    
    def _save_sleep_periods(self, data: List[Dict], data_type: str) -> int:
        """Save sleep period data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Extract raw data if present
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(SleepPeriod).values(
                        period_id=record.get('period_id') or raw_data.get('id', f"unknown_{count}"),
                        date=record.get('date'),
                        type=record.get('type'),
                        score=record.get('score'),
                        bedtime_start=record.get('bedtime_start'),
                        bedtime_end=record.get('bedtime_end'),
                        total_sleep_hours=record.get('total_sleep_hours'),
                        time_in_bed_hours=record.get('time_in_bed_hours'),
                        rem_hours=record.get('rem_hours'),
                        deep_hours=record.get('deep_hours'),
                        light_hours=record.get('light_hours'),
                        awake_time=record.get('awake_time'),
                        rem_percentage=record.get('rem_percentage'),
                        deep_percentage=record.get('deep_percentage'),
                        light_percentage=record.get('light_percentage'),
                        efficiency_percent=record.get('efficiency_percent'),
                        latency_minutes=record.get('latency_minutes'),
                        restless_periods=record.get('restless_periods'),
                        heart_rate_avg=record.get('heart_rate_avg'),
                        heart_rate_min=record.get('heart_rate_min'),
                        hrv_avg=record.get('hrv_avg'),
                        hrv_max=record.get('hrv_max'),
                        hrv_min=record.get('hrv_min'),
                        hrv_stdev=record.get('hrv_stdev'),
                        respiratory_rate=record.get('respiratory_rate'),
                        has_heart_rate_data=record.get('has_heart_rate_data'),
                        has_hrv_data=record.get('has_hrv_data'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['period_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving sleep period {record.get('period_id')}: {e}")
            
            logger.info(f"Saved {count} sleep period records")
            return count
    
    def _save_daily_sleep(self, data: List[Dict], data_type: str) -> int:
        """Save daily sleep data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(DailySleep).values(
                        date=record.get('date'),
                        sleep_score=record.get('sleep_score'),
                        timestamp=record.get('timestamp'),
                        score_deep_sleep=record.get('score_deep_sleep'),
                        score_efficiency=record.get('score_efficiency'),
                        score_latency=record.get('score_latency'),
                        score_rem_sleep=record.get('score_rem_sleep'),
                        score_restfulness=record.get('score_restfulness'),
                        score_timing=record.get('score_timing'),
                        score_total_sleep=record.get('score_total_sleep'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving daily sleep for {record.get('date')}: {e}")
            
            logger.info(f"Saved {count} daily sleep records")
            return count
    
    def _save_activity(self, data: List[Dict], data_type: str) -> int:
        """Save activity data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(Activity).values(
                        date=record.get('date'),
                        activity_score=record.get('activity_score'),
                        steps=record.get('steps'),
                        distance_km=record.get('distance_km'),
                        calories_active=record.get('calories_active'),
                        calories_total=record.get('calories_total'),
                        calories_target=record.get('calories_target'),
                        high_activity_minutes=record.get('high_activity_minutes'),
                        medium_activity_minutes=record.get('medium_activity_minutes'),
                        low_activity_minutes=record.get('low_activity_minutes'),
                        sedentary_minutes=record.get('sedentary_minutes'),
                        non_wear_minutes=record.get('non_wear_minutes'),
                        total_active_minutes=record.get('total_active_minutes'),
                        met_minutes=record.get('met_minutes'),
                        average_met=record.get('average_met'),
                        high_activity_met_minutes=record.get('high_activity_met_minutes'),
                        medium_activity_met_minutes=record.get('medium_activity_met_minutes'),
                        low_activity_met_minutes=record.get('low_activity_met_minutes'),
                        inactivity_alerts=record.get('inactivity_alerts'),
                        resting_time_minutes=record.get('resting_time_minutes'),
                        score_meet_daily_targets=record.get('score_meet_daily_targets'),
                        score_move_every_hour=record.get('score_move_every_hour'),
                        score_recovery_time=record.get('score_recovery_time'),
                        score_stay_active=record.get('score_stay_active'),
                        score_training_frequency=record.get('score_training_frequency'),
                        score_training_volume=record.get('score_training_volume'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving activity for {record.get('date')}: {e}")
            
            logger.info(f"Saved {count} activity records")
            return count
    
    def _save_readiness(self, data: List[Dict], data_type: str) -> int:
        """Save readiness data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(Readiness).values(
                        date=record.get('date'),
                        readiness_score=record.get('readiness_score'),
                        temperature_deviation=record.get('temperature_deviation'),
                        temperature_trend_deviation=record.get('temperature_trend_deviation'),
                        recovery_index=record.get('recovery_index'),
                        resting_heart_rate=record.get('resting_heart_rate'),
                        hrv_balance=record.get('hrv_balance'),
                        score_activity_balance=record.get('score_activity_balance'),
                        score_body_temperature=record.get('score_body_temperature'),
                        score_hrv_balance=record.get('score_hrv_balance'),
                        score_previous_day_activity=record.get('score_previous_day_activity'),
                        score_previous_night=record.get('score_previous_night'),
                        score_recovery_index=record.get('score_recovery_index'),
                        score_resting_heart_rate=record.get('score_resting_heart_rate'),
                        score_sleep_balance=record.get('score_sleep_balance'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving readiness for {record.get('date')}: {e}")
            
            logger.info(f"Saved {count} readiness records")
            return count
    
    def _save_workouts(self, data: List[Dict], data_type: str) -> int:
        """Save workout data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(Workout).values(
                        workout_id=record.get('workout_id') or raw_data.get('id', f"unknown_{count}"),
                        date=record.get('date'),
                        activity=record.get('activity'),
                        intensity=record.get('intensity'),
                        label=record.get('label'),
                        source=record.get('source'),
                        start_datetime=record.get('start_datetime'),
                        end_datetime=record.get('end_datetime'),
                        duration_minutes=record.get('duration_minutes'),
                        calories=record.get('calories'),
                        distance_meters=record.get('distance_meters'),
                        distance_km=record.get('distance_km'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['workout_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving workout {record.get('workout_id')}: {e}")
            
            logger.info(f"Saved {count} workout records")
            return count
    
    def _save_stress(self, data: List[Dict], data_type: str) -> int:
        """Save stress data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    raw_data = record.get('raw_data', {})
                    
                    stmt = insert(Stress).values(
                        date=record.get('date'),
                        stress_high_minutes=record.get('stress_high_minutes'),
                        recovery_high_minutes=record.get('recovery_high_minutes'),
                        day_summary=record.get('day_summary'),
                        stress_recovery_ratio=record.get('stress_recovery_ratio'),
                        raw_data=raw_data if raw_data else record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving stress for {record.get('date')}: {e}")
            
            logger.info(f"Saved {count} stress records")
            return count
    
    def _save_heart_rate(self, data: List[Dict], data_type: str) -> int:
        """Save heart rate time series data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Handle the Oura API response format
                    if 'data' in record:
                        # This is a full API response with nested data
                        for data_item in record['data']:
                            timestamp = data_item.get('timestamp')
                            bpm = data_item.get('bpm')
                            if timestamp and bpm is not None:
                                hr_record = HeartRate(
                                    timestamp=timestamp,
                                    heart_rate=bpm,
                                    source=data_item.get('source', 'oura')
                                )
                                session.add(hr_record)
                                count += 1
                    elif 'timestamp' in record and 'bpm' in record:
                        # Direct heart rate record
                        hr_record = HeartRate(
                            timestamp=record['timestamp'],
                            heart_rate=record['bpm'],
                            source=record.get('source', 'oura')
                        )
                        session.add(hr_record)
                        count += 1
                    elif 'timestamp' in record and 'heart_rate' in record:
                        # Alternative format
                        hr_record = HeartRate(
                            timestamp=record['timestamp'],
                            heart_rate=record['heart_rate'],
                            source=record.get('source', 'oura')
                        )
                        session.add(hr_record)
                        count += 1
                except Exception as e:
                    logger.error(f"Error saving heart rate data: {e}")
                    logger.debug(f"Record structure: {record}")
            
            logger.info(f"Saved {count} heart rate records")
            return count
    
    def _save_daily_summaries(self, data: List[Dict], data_type: str) -> int:
        """Save daily summary data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(DailySummary).values(
                        date=record.get('date'),
                        overall_health_score=record.get('overall_health_score'),
                        total_sleep_periods=record.get('total_sleep_periods'),
                        total_workouts=record.get('total_workouts'),
                        insights=record.get('insights'),
                        sleep_periods_data=record.get('sleep_periods'),
                        daily_sleep_data=record.get('daily_sleep_score'),
                        activity_data=record.get('activity'),
                        readiness_data=record.get('readiness'),
                        stress_data=record.get('stress'),
                        workouts_data=record.get('workouts')
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving daily summary for {record.get('date')}: {e}")
            
            logger.info(f"Saved {count} daily summary records")
            return count
    
    def _save_sessions(self, data: List[Dict], data_type: str) -> int:
        """Save session data (breathing, meditation, etc.)"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Process the session data if needed
                    if 'session_id' in record:
                        # Already processed
                        session_data = record
                    else:
                        # Raw data from API
                        session_data = {
                            'session_id': record.get('id'),
                            'date': record.get('day'),
                            'type': record.get('type'),
                            'mood': record.get('mood'),
                            'start_datetime': record.get('start_datetime'),
                            'end_datetime': record.get('end_datetime'),
                            'heart_rate_data': record.get('heart_rate', {}),
                            'hrv_data': record.get('heart_rate_variability', {}),
                            'motion_count_data': record.get('motion_count', {}),
                            'raw_data': record
                        }
                        
                        # Calculate duration if possible
                        if record.get('start_datetime') and record.get('end_datetime'):
                            try:
                                start = datetime.fromisoformat(record['start_datetime'].replace('Z', '+00:00'))
                                end = datetime.fromisoformat(record['end_datetime'].replace('Z', '+00:00'))
                                session_data['duration_minutes'] = round((end - start).total_seconds() / 60, 1)
                            except:
                                pass
                    
                    stmt = insert(Session).values(
                        session_id=session_data.get('session_id'),
                        date=session_data.get('date'),
                        type=session_data.get('type'),
                        mood=session_data.get('mood'),
                        start_datetime=session_data.get('start_datetime'),
                        end_datetime=session_data.get('end_datetime'),
                        duration_minutes=session_data.get('duration_minutes'),
                        heart_rate_data=session_data.get('heart_rate_data'),
                        hrv_data=session_data.get('hrv_data'),
                        motion_count_data=session_data.get('motion_count_data'),
                        raw_data=session_data.get('raw_data', record)
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['session_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving session {record.get('id')}: {e}")
            
            logger.info(f"Saved {count} session records")
            return count
    
    def _save_vo2_max(self, data: List[Dict], data_type: str) -> int:
        """Save VO2 max data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(VO2Max).values(
                        date=record.get('day'),
                        vo2_max=record.get('vo2_max'),
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving VO2 max for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} VO2 max records")
            return count
    
    def _save_cardiovascular_age(self, data: List[Dict], data_type: str) -> int:
        """Save cardiovascular age data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(CardiovascularAge).values(
                        date=record.get('day'),
                        cardiovascular_age=record.get('vascular_age'),  # Fixed column name
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving cardiovascular age for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} cardiovascular age records")
            return count
    
    def _save_resilience_data(self, data: List[Dict], data_type: str) -> int:
        """Save resilience data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    contributors = record.get('contributors', {})
                    
                    stmt = insert(Resilience).values(
                        resilience_id=record.get('id', f"unknown_{count}"),
                        date=record.get('day'),
                        resilience_level=record.get('level'),  # Fixed column name
                        sleep_recovery=contributors.get('sleep_recovery'),
                        daytime_recovery=contributors.get('daytime_recovery'),
                        stress=contributors.get('stress'),
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['resilience_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving resilience for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} resilience records")
            return count
    
    def _save_spo2(self, data: List[Dict], data_type: str) -> int:
        """Save SpO2 (blood oxygen) data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Extract SpO2 percentage average
                    spo2_avg = None
                    if 'spo2_percentage' in record:
                        spo2_data = record['spo2_percentage']
                        if isinstance(spo2_data, dict):
                            spo2_avg = spo2_data.get('average')
                    
                    # Extract breathing disturbance index
                    bdi = None
                    if 'breathing_disturbance_index' in record:
                        bdi = record['breathing_disturbance_index']
                    
                    stmt = insert(SpO2).values(
                        date=record.get('day'),
                        spo2_percentage_avg=spo2_avg,
                        breathing_disturbance_index=bdi,
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving SpO2 for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} SpO2 records")
            return count
    
    def _save_tags(self, data: List[Dict], data_type: str) -> int:
        """Save enhanced tags data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Tags might come as a list or string
                    tags = record.get('tags', [])
                    if isinstance(tags, list):
                        tags_str = json.dumps(tags)
                    else:
                        tags_str = str(tags)
                    
                    tag_record = Tag(
                        date=record.get('day'),
                        tag_type=record.get('tag_type_code', 'general'),
                        tags=tags_str,
                        raw_data=record
                    )
                    session.add(tag_record)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving tags for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} tag records")
            return count
    
    def _save_sleep_time(self, data: List[Dict], data_type: str) -> int:
        """Save sleep time recommendations"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    # Extract recommendation text
                    recommendation = record.get('recommendation', '')
                    if isinstance(recommendation, dict):
                        recommendation = json.dumps(recommendation)
                    
                    stmt = insert(SleepTime).values(
                        date=record.get('day'),
                        recommendation=recommendation,
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving sleep time for {record.get('day')}: {e}")
            
            logger.info(f"Saved {count} sleep time records")
            return count
    
    def _save_rest_mode_periods(self, data: List[Dict], data_type: str) -> int:
        """Save rest mode periods"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(RestModePeriod).values(
                        rest_mode_period_id=record.get('id', f"unknown_{count}"),
                        start_date=record.get('start_day'),
                        end_date=record.get('end_day'),
                        rest_mode_state=record.get('rest_mode_state'),
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['rest_mode_period_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving rest mode period {record.get('id')}: {e}")
            
            logger.info(f"Saved {count} rest mode period records")
            return count
    
    def _save_ring_configuration(self, data: List[Dict], data_type: str) -> int:
        """Save ring configuration data"""
        with self.get_session() as session:
            count = 0
            for record in data:
                try:
                    stmt = insert(RingConfiguration).values(
                        ring_id=record.get('id', f"unknown_{count}"),
                        color=record.get('color'),
                        design=record.get('design'),
                        firmware_version=record.get('firmware_version'),
                        hardware_type=record.get('hardware_type'),
                        set_up_at=record.get('set_up_at'),
                        size=record.get('size'),
                        raw_data=record
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ring_id'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    count += 1
                except Exception as e:
                    logger.error(f"Error saving ring configuration {record.get('id')}: {e}")
            
            logger.info(f"Saved {count} ring configuration records")
            return count
    
    def _save_raw_data(self, data: List[Dict], data_type: str) -> int:
        """Save raw data that doesn't have a specific table
        
        This data is typically stored in the raw_data JSON field of related tables
        or logged for future processing.
        """
        logger.info(f"Received {len(data)} {data_type} records (stored as raw JSON)")
        # For now, just log that we received this data
        # In a real implementation, you might want to store this in a generic table
        # or process it differently
        return len(data)
    
    def save_collection_summary(self, summary: Dict[str, Any]) -> None:
        """Save collection summary as a log entry
        
        Args:
            summary: Collection summary data
        """
        with self.get_session() as session:
            try:
                # Calculate totals from results
                total_records = 0
                successful_endpoints = 0
                failed_endpoints = 0
                errors = []
                
                for data_type, result in summary.get('results', {}).items():
                    if 'error' in result:
                        failed_endpoints += 1
                        errors.append(f"{data_type}: {result['error']}")
                    else:
                        successful_endpoints += 1
                        records = (result.get('records_collected', 0) or 
                                 result.get('records_processed', 0) or 
                                 result.get('records_created', 0))
                        total_records += records
                
                log_entry = CollectionLog(
                    collection_time=datetime.fromisoformat(summary['collection_time']),
                    start_date=summary.get('start_date'),
                    end_date=summary.get('end_date'),
                    results=summary.get('results'),
                    total_records=total_records,
                    successful_endpoints=successful_endpoints,
                    failed_endpoints=failed_endpoints,
                    errors=errors if errors else None
                )
                session.add(log_entry)
                
                logger.info(f"Saved collection summary: {total_records} records from "
                          f"{successful_endpoints} endpoints (failed: {failed_endpoints})")
                
            except Exception as e:
                logger.error(f"Failed to save collection summary: {e}")
                raise
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("Database connections closed")
