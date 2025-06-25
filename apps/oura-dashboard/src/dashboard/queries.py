"""Database queries for Oura data visualization"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import numpy as np

# Import the database models
from database_models import (
    Base, PersonalInfo, SleepPeriod, DailySleep, Activity, 
    Readiness, Workout, Stress, HeartRate, DailySummary
)

class OuraDataQueries:
    """Query interface for Oura health data"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection
        
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
    
    def get_date_range(self) -> Tuple[date, date]:
        """Get the date range of available data
        
        Returns:
            Tuple of (min_date, max_date)
        """
        with self.get_session() as session:
            result = session.query(
                func.min(DailySummary.date),
                func.max(DailySummary.date)
            ).first()
            
            if result and result[0]:
                return result[0], result[1]
            
            # Fallback to activity data
            result = session.query(
                func.min(Activity.date),
                func.max(Activity.date)
            ).first()
            
            if result and result[0]:
                return result[0], result[1]
                
            # Default to last 30 days
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            return start_date, end_date
    
    def get_personal_info(self) -> Dict[str, Any]:
        """Get personal information
        
        Returns:
            Personal info dictionary
        """
        with self.get_session() as session:
            info = session.query(PersonalInfo).order_by(
                PersonalInfo.updated_at.desc()
            ).first()
            
            if info:
                return {
                    'user_id': info.user_id,
                    'age': info.age,
                    'weight': info.weight,
                    'height': info.height,
                    'biological_sex': info.biological_sex,
                    'email': info.email,
                    'updated_at': info.updated_at
                }
            return {}
    
    def get_daily_summary_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get daily summary data as DataFrame
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with daily summaries
        """
        with self.get_session() as session:
            # Query all relevant daily data
            query = session.query(
                DailySummary.date,
                DailySummary.overall_health_score,
                DailySleep.sleep_score,
                Activity.activity_score,
                Activity.steps,
                Activity.calories_total,
                Activity.total_active_minutes,
                Readiness.readiness_score,
                Readiness.temperature_deviation,
                Readiness.hrv_balance,
                Readiness.resting_heart_rate,
                Stress.stress_high_minutes,
                Stress.recovery_high_minutes,
                Stress.stress_recovery_ratio
            ).outerjoin(
                DailySleep, DailySummary.date == DailySleep.date
            ).outerjoin(
                Activity, DailySummary.date == Activity.date
            ).outerjoin(
                Readiness, DailySummary.date == Readiness.date
            ).outerjoin(
                Stress, DailySummary.date == Stress.date
            ).filter(
                DailySummary.date.between(start_date, end_date)
            ).order_by(DailySummary.date)
            
            results = query.all()
            
            if results:
                df = pd.DataFrame(results)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            # Fallback if no daily summaries exist
            return self._get_daily_data_fallback(start_date, end_date)
    
    def _get_daily_data_fallback(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get daily data without DailySummary table"""
        with self.get_session() as session:
            # Query from individual tables
            sleep_q = session.query(
                DailySleep.date,
                DailySleep.sleep_score
            ).filter(DailySleep.date.between(start_date, end_date)).subquery()
            
            activity_q = session.query(
                Activity.date,
                Activity.activity_score,
                Activity.steps,
                Activity.calories_total,
                Activity.total_active_minutes
            ).filter(Activity.date.between(start_date, end_date)).subquery()
            
            readiness_q = session.query(
                Readiness.date,
                Readiness.readiness_score,
                Readiness.temperature_deviation,
                Readiness.hrv_balance,
                Readiness.resting_heart_rate
            ).filter(Readiness.date.between(start_date, end_date)).subquery()
            
            # Create a date series
            dates = pd.date_range(start_date, end_date, freq='D')
            df = pd.DataFrame({'date': dates})
            
            # Fetch and merge data
            for table, alias in [(sleep_q, 'sleep'), (activity_q, 'activity'), (readiness_q, 'readiness')]:
                data = session.query(table).all()
                if data:
                    temp_df = pd.DataFrame(data)
                    temp_df['date'] = pd.to_datetime(temp_df['date'])
                    df = df.merge(temp_df, on='date', how='left')
            
            # Calculate overall health score
            score_cols = ['sleep_score', 'activity_score', 'readiness_score']
            existing_cols = [col for col in score_cols if col in df.columns]
            if existing_cols:
                df['overall_health_score'] = df[existing_cols].mean(axis=1)
            
            return df
    
    def get_sleep_periods_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get detailed sleep period data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with sleep periods
        """
        with self.get_session() as session:
            periods = session.query(SleepPeriod).filter(
                SleepPeriod.date.between(start_date, end_date)
            ).order_by(SleepPeriod.date).all()
            
            if periods:
                data = []
                for p in periods:
                    data.append({
                        'date': p.date,
                        'type': p.type,
                        'total_sleep_hours': p.total_sleep_hours,
                        'time_in_bed_hours': p.time_in_bed_hours,
                        'efficiency_percent': p.efficiency_percent,
                        'rem_hours': p.rem_hours,
                        'deep_hours': p.deep_hours,
                        'light_hours': p.light_hours,
                        'awake_time': p.awake_time,
                        'rem_percentage': p.rem_percentage,
                        'deep_percentage': p.deep_percentage,
                        'light_percentage': p.light_percentage,
                        'latency_minutes': p.latency_minutes,
                        'heart_rate_avg': p.heart_rate_avg,
                        'hrv_avg': p.hrv_avg,
                        'respiratory_rate': p.respiratory_rate
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            return pd.DataFrame()
    
    def get_activity_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get activity data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with activity data
        """
        with self.get_session() as session:
            activities = session.query(Activity).filter(
                Activity.date.between(start_date, end_date)
            ).order_by(Activity.date).all()
            
            if activities:
                data = []
                for a in activities:
                    data.append({
                        'date': a.date,
                        'activity_score': a.activity_score,
                        'steps': a.steps,
                        'distance_km': a.distance_km,
                        'calories_active': a.calories_active,
                        'calories_total': a.calories_total,
                        'high_activity_minutes': a.high_activity_minutes,
                        'medium_activity_minutes': a.medium_activity_minutes,
                        'low_activity_minutes': a.low_activity_minutes,
                        'sedentary_minutes': a.sedentary_minutes,
                        'total_active_minutes': a.total_active_minutes,
                        'met_minutes': a.met_minutes,
                        'inactivity_alerts': a.inactivity_alerts
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            return pd.DataFrame()
    
    def get_readiness_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get readiness data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with readiness data
        """
        with self.get_session() as session:
            readiness = session.query(Readiness).filter(
                Readiness.date.between(start_date, end_date)
            ).order_by(Readiness.date).all()
            
            if readiness:
                data = []
                for r in readiness:
                    data.append({
                        'date': r.date,
                        'readiness_score': r.readiness_score,
                        'temperature_deviation': r.temperature_deviation,
                        'temperature_trend_deviation': r.temperature_trend_deviation,
                        'recovery_index': r.recovery_index,
                        'resting_heart_rate': r.resting_heart_rate,
                        'hrv_balance': r.hrv_balance,
                        'score_activity_balance': r.score_activity_balance,
                        'score_body_temperature': r.score_body_temperature,
                        'score_hrv_balance': r.score_hrv_balance,
                        'score_previous_night': r.score_previous_night,
                        'score_recovery_index': r.score_recovery_index,
                        'score_resting_heart_rate': r.score_resting_heart_rate
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            return pd.DataFrame()
    
    def get_workouts_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get workout data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with workout data
        """
        with self.get_session() as session:
            workouts = session.query(Workout).filter(
                Workout.date.between(start_date, end_date)
            ).order_by(Workout.date).all()
            
            if workouts:
                data = []
                for w in workouts:
                    data.append({
                        'date': w.date,
                        'activity': w.activity,
                        'intensity': w.intensity,
                        'duration_minutes': w.duration_minutes,
                        'calories': w.calories,
                        'distance_km': w.distance_km,
                        'source': w.source,
                        'label': w.label
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            return pd.DataFrame()
    
    def get_stress_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get stress data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with stress data
        """
        with self.get_session() as session:
            stress = session.query(Stress).filter(
                Stress.date.between(start_date, end_date)
            ).order_by(Stress.date).all()
            
            if stress:
                data = []
                for s in stress:
                    data.append({
                        'date': s.date,
                        'stress_high_minutes': s.stress_high_minutes,
                        'recovery_high_minutes': s.recovery_high_minutes,
                        'stress_recovery_ratio': s.stress_recovery_ratio,
                        'day_summary': s.day_summary
                    })
                
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
            
            return pd.DataFrame()
    
    def get_heart_rate_df(self, start_datetime: datetime, end_datetime: datetime) -> pd.DataFrame:
        """Get heart rate time series data
        
        Args:
            start_datetime: Start datetime
            end_datetime: End datetime
            
        Returns:
            DataFrame with heart rate data
        """
        with self.get_session() as session:
            hr_data = session.query(HeartRate).filter(
                HeartRate.timestamp.between(start_datetime, end_datetime)
            ).order_by(HeartRate.timestamp).all()
            
            if hr_data:
                data = []
                for hr in hr_data:
                    data.append({
                        'timestamp': hr.timestamp,
                        'heart_rate': hr.heart_rate,
                        'source': hr.source
                    })
                
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            
            return pd.DataFrame()
    
    def get_sleep_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get sleep trends for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with sleep trend statistics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        df = self.get_sleep_periods_df(start_date, end_date)
        
        if df.empty:
            return {}
        
        # Filter for main sleep periods only
        df_main = df[df['type'] == 'long_sleep']
        
        return {
            'avg_sleep_hours': df_main['total_sleep_hours'].mean(),
            'avg_efficiency': df_main['efficiency_percent'].mean(),
            'avg_rem_percent': df_main['rem_percentage'].mean(),
            'avg_deep_percent': df_main['deep_percentage'].mean(),
            'avg_light_percent': df_main['light_percentage'].mean(),
            'avg_hrv': df_main['hrv_avg'].mean(),
            'avg_heart_rate': df_main['heart_rate_avg'].mean(),
            'trend_sleep_hours': self._calculate_trend(df_main, 'total_sleep_hours'),
            'trend_efficiency': self._calculate_trend(df_main, 'efficiency_percent'),
            'trend_hrv': self._calculate_trend(df_main, 'hrv_avg')
        }
    
    def get_activity_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get activity trends for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with activity trend statistics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        df = self.get_activity_df(start_date, end_date)
        
        if df.empty:
            return {}
        
        return {
            'avg_steps': df['steps'].mean(),
            'avg_active_minutes': df['total_active_minutes'].mean(),
            'avg_calories': df['calories_total'].mean(),
            'total_distance_km': df['distance_km'].sum(),
            'avg_activity_score': df['activity_score'].mean(),
            'trend_steps': self._calculate_trend(df, 'steps'),
            'trend_active_minutes': self._calculate_trend(df, 'total_active_minutes'),
            'days_above_10k_steps': len(df[df['steps'] >= 10000]),
            'sedentary_percentage': (df['sedentary_minutes'].mean() / (24 * 60)) * 100
        }
    
    def get_health_correlations(self, days: int = 30) -> pd.DataFrame:
        """Calculate correlations between health metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Correlation matrix DataFrame
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        df = self.get_daily_summary_df(start_date, end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        # Select numeric columns for correlation
        corr_cols = [
            'sleep_score', 'activity_score', 'readiness_score',
            'steps', 'total_active_minutes', 'hrv_balance',
            'resting_heart_rate', 'temperature_deviation'
        ]
        
        existing_cols = [col for col in corr_cols if col in df.columns]
        
        if existing_cols:
            return df[existing_cols].corr()
        
        return pd.DataFrame()
    
    def get_weekly_summary(self, weeks: int = 4) -> pd.DataFrame:
        """Get weekly summary statistics
        
        Args:
            weeks: Number of weeks to analyze
            
        Returns:
            DataFrame with weekly summaries
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks * 7)
        
        df = self.get_daily_summary_df(start_date, end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        # Add week information
        df['week'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.year
        
        # Group by week
        weekly = df.groupby(['year', 'week']).agg({
            'sleep_score': 'mean',
            'activity_score': 'mean',
            'readiness_score': 'mean',
            'overall_health_score': 'mean',
            'steps': 'mean',
            'total_active_minutes': 'mean',
            'hrv_balance': 'mean',
            'resting_heart_rate': 'mean'
        }).round(1)
        
        weekly.reset_index(inplace=True)
        weekly['week_start'] = weekly.apply(
            lambda x: datetime.strptime(f"{x['year']}-W{x['week']}-1", "%Y-W%W-%w").date(),
            axis=1
        )
        
        return weekly
    
    def _calculate_trend(self, df: pd.DataFrame, column: str) -> str:
        """Calculate trend direction for a metric
        
        Args:
            df: DataFrame with date index
            column: Column to analyze
            
        Returns:
            'increasing', 'decreasing', or 'stable'
        """
        if df.empty or column not in df.columns:
            return 'unknown'
        
        # Remove NaN values
        values = df[column].dropna()
        
        if len(values) < 3:
            return 'insufficient_data'
        
        # Calculate linear regression slope
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        # Determine trend based on slope
        if abs(slope) < 0.01:  # Threshold for "stable"
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()