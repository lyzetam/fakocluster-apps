"""Database models for Oura data storage"""
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Date, Boolean, JSON, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class PersonalInfo(Base):
    """Personal information from Oura"""
    __tablename__ = 'oura_personal_info'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    age = Column(Integer)
    weight = Column(Float)
    height = Column(Float)
    biological_sex = Column(String(20))
    email = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)

class SleepPeriod(Base):
    """Detailed sleep period data"""
    __tablename__ = 'oura_sleep_periods'
    
    id = Column(Integer, primary_key=True)
    period_id = Column(String(50), unique=True, nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50))
    score = Column(Integer)
    
    # Time metrics
    bedtime_start = Column(DateTime)
    bedtime_end = Column(DateTime)
    total_sleep_hours = Column(Float)
    time_in_bed_hours = Column(Float)
    
    # Sleep stages
    rem_hours = Column(Float)
    deep_hours = Column(Float)
    light_hours = Column(Float)
    awake_time = Column(Float)
    
    # Percentages
    rem_percentage = Column(Float)
    deep_percentage = Column(Float)
    light_percentage = Column(Float)
    
    # Efficiency and quality
    efficiency_percent = Column(Float)
    latency_minutes = Column(Float)
    restless_periods = Column(Integer)
    
    # Physiological metrics
    heart_rate_avg = Column(Float)
    heart_rate_min = Column(Float)
    hrv_avg = Column(Float)
    hrv_max = Column(Float)
    hrv_min = Column(Float)
    hrv_stdev = Column(Float)
    respiratory_rate = Column(Float)
    
    # Additional flags
    has_heart_rate_data = Column(Boolean)
    has_hrv_data = Column(Boolean)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_sleep_date', 'date'),)

class DailySleep(Base):
    """Daily sleep scores and contributors"""
    __tablename__ = 'oura_daily_sleep'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    sleep_score = Column(Integer)
    timestamp = Column(DateTime)
    
    # Contributors
    score_deep_sleep = Column(Integer)
    score_efficiency = Column(Integer)
    score_latency = Column(Integer)
    score_rem_sleep = Column(Integer)
    score_restfulness = Column(Integer)
    score_timing = Column(Integer)
    score_total_sleep = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_daily_sleep_date', 'date'),)

class Activity(Base):
    """Daily activity data"""
    __tablename__ = 'oura_activity'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    activity_score = Column(Integer)
    steps = Column(Integer)
    distance_km = Column(Float)
    
    # Calories
    calories_active = Column(Integer)
    calories_total = Column(Integer)
    calories_target = Column(Integer)
    
    # Activity time breakdown
    high_activity_minutes = Column(Float)
    medium_activity_minutes = Column(Float)
    low_activity_minutes = Column(Float)
    sedentary_minutes = Column(Float)
    non_wear_minutes = Column(Float)
    total_active_minutes = Column(Float)
    
    # MET metrics
    met_minutes = Column(Float)
    average_met = Column(Float)
    high_activity_met_minutes = Column(Float)
    medium_activity_met_minutes = Column(Float)
    low_activity_met_minutes = Column(Float)
    
    # Other metrics
    inactivity_alerts = Column(Integer)
    resting_time_minutes = Column(Float)
    
    # Contributors
    score_meet_daily_targets = Column(Integer)
    score_move_every_hour = Column(Integer)
    score_recovery_time = Column(Integer)
    score_stay_active = Column(Integer)
    score_training_frequency = Column(Integer)
    score_training_volume = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_activity_date', 'date'),)

class Readiness(Base):
    """Daily readiness data"""
    __tablename__ = 'oura_readiness'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    readiness_score = Column(Integer)
    
    # Temperature metrics
    temperature_deviation = Column(Float)
    temperature_trend_deviation = Column(Float)
    
    # Recovery metrics
    recovery_index = Column(Float)
    resting_heart_rate = Column(Float)
    hrv_balance = Column(Float)
    
    # Contributors
    score_activity_balance = Column(Integer)
    score_body_temperature = Column(Integer)
    score_hrv_balance = Column(Integer)
    score_previous_day_activity = Column(Integer)
    score_previous_night = Column(Integer)
    score_recovery_index = Column(Integer)
    score_resting_heart_rate = Column(Integer)
    score_sleep_balance = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_readiness_date', 'date'),)

class Workout(Base):
    """Workout data"""
    __tablename__ = 'oura_workouts'
    
    id = Column(Integer, primary_key=True)
    workout_id = Column(String(50), unique=True, nullable=False)
    date = Column(Date, nullable=False)
    activity = Column(String(100))
    intensity = Column(String(50))
    label = Column(String(255))
    source = Column(String(100))
    
    # Time metrics
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    duration_minutes = Column(Float)
    
    # Performance metrics
    calories = Column(Integer)
    distance_meters = Column(Float)
    distance_km = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_workout_date', 'date'),)

class Stress(Base):
    """Daily stress data"""
    __tablename__ = 'oura_stress'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    stress_high_minutes = Column(Integer)
    recovery_high_minutes = Column(Integer)
    day_summary = Column(Text)
    stress_recovery_ratio = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_stress_date', 'date'),)

class HeartRate(Base):
    """Heart rate time series data"""
    __tablename__ = 'oura_heart_rate'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    heart_rate = Column(Integer)
    source = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_heart_rate_timestamp', 'timestamp'),)

class Session(Base):
    """Session data (breathing, meditation, etc.)"""
    __tablename__ = 'oura_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(50), unique=True, nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50))  # breathing, meditation, etc.
    mood = Column(String(50))
    
    # Time metrics
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    duration_minutes = Column(Float)
    
    # Time series data stored as JSON
    heart_rate_data = Column(JSON)
    hrv_data = Column(JSON)
    motion_count_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_session_date', 'date'),)

class VO2Max(Base):
    """VO2 Max data"""
    __tablename__ = 'oura_vo2_max'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    vo2_max = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_vo2_max_date', 'date'),)

class CardiovascularAge(Base):
    """Cardiovascular Age data"""
    __tablename__ = 'oura_cardiovascular_age'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    cardiovascular_age = Column(Integer)  # Fixed column name
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_cardiovascular_age_date', 'date'),)

class Resilience(Base):
    """Daily Resilience data"""
    __tablename__ = 'oura_resilience'
    
    id = Column(Integer, primary_key=True)
    resilience_id = Column(String(50), unique=True, nullable=False)
    date = Column(Date, unique=True, nullable=False)
    resilience_level = Column(String(50))  # limited, adequate, solid, strong
    
    # Contributors
    sleep_recovery = Column(Float)
    daytime_recovery = Column(Float)
    stress = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_resilience_date', 'date'),)

class SpO2(Base):
    """Daily SpO2 (blood oxygen) data"""
    __tablename__ = 'oura_spo2'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    spo2_percentage_avg = Column(Float)
    breathing_disturbance_index = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_spo2_date', 'date'),)

class Tag(Base):
    """Enhanced tags data"""
    __tablename__ = 'oura_tags'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    tag_type = Column(String(50))
    tags = Column(Text)  # Comma-separated or JSON array
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_tags_date', 'date'),)

class SleepTime(Base):
    """Sleep time recommendations"""
    __tablename__ = 'oura_sleep_time'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    recommendation = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_sleep_time_date', 'date'),)

class RestModePeriod(Base):
    """Rest mode periods"""
    __tablename__ = 'oura_rest_mode_periods'
    
    id = Column(Integer, primary_key=True)
    rest_mode_period_id = Column(String(50), unique=True, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # Nullable for ongoing periods
    rest_mode_state = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)
    
    __table_args__ = (Index('idx_rest_mode_start', 'start_date'),)

class RingConfiguration(Base):
    """Ring configuration data"""
    __tablename__ = 'oura_ring_configuration'
    
    id = Column(Integer, primary_key=True)
    ring_id = Column(String(50), unique=True, nullable=False)
    color = Column(String(50))
    design = Column(String(50))
    firmware_version = Column(String(50))
    hardware_type = Column(String(50))
    set_up_at = Column(DateTime)
    size = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)

class DailySummary(Base):
    """Comprehensive daily summaries"""
    __tablename__ = 'oura_daily_summaries'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    overall_health_score = Column(Float)
    
    # Counts
    total_sleep_periods = Column(Integer)
    total_workouts = Column(Integer)
    
    # Insights stored as JSON
    insights = Column(JSON)
    
    # References to primary data (stored as JSON)
    sleep_periods_data = Column(JSON)
    daily_sleep_data = Column(JSON)
    activity_data = Column(JSON)
    readiness_data = Column(JSON)
    stress_data = Column(JSON)
    workouts_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_summary_date', 'date'),)

class CollectionLog(Base):
    """Track collection runs and statistics"""
    __tablename__ = 'oura_collection_logs'
    
    id = Column(Integer, primary_key=True)
    collection_time = Column(DateTime, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Results summary
    results = Column(JSON)
    total_records = Column(Integer)
    successful_endpoints = Column(Integer)
    failed_endpoints = Column(Integer)
    errors = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
