"""Database queries for Oura data visualization - Simplified version"""
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)

class OuraDataQueries:
    """Query interface for Oura health data - Direct SQL queries"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self._create_engine()
        
    def _create_engine(self):
        """Create database engine with connection pooling"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    
    def _execute_query(self, query: str, params: Dict = None) -> pd.DataFrame:
        """Execute a query with retry logic and return results as DataFrame
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query results as DataFrame
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # For SQLAlchemy 2.0+, we need to use connection.execute with text()
                with self.engine.connect() as conn:
                    result = conn.execute(text(query), params or {})
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    return df
            except OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database query error (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
                    # Try to recreate the engine
                    try:
                        self._create_engine()
                    except Exception:
                        pass
                else:
                    logger.error(f"Database query failed after {max_retries} attempts: {e}")
                    raise
    
    def get_date_range(self) -> Tuple[date, date]:
        """Get the date range of available data"""
        try:
            query = """
            SELECT 
                COALESCE(MIN(date), CURRENT_DATE - INTERVAL '30 days')::date as min_date,
                COALESCE(MAX(date), CURRENT_DATE)::date as max_date
            FROM (
                SELECT date FROM oura_daily_summaries
                UNION ALL
                SELECT date FROM oura_activity
                UNION ALL
                SELECT date FROM oura_daily_sleep
            ) combined_dates
            """
            df = self._execute_query(query)
            if not df.empty:
                return df.iloc[0]['min_date'], df.iloc[0]['max_date']
        except Exception as e:
            logger.error(f"Failed to get date range: {e}")
        
        # Default to last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date
    
    def get_personal_info(self) -> Dict[str, Any]:
        """Get personal information"""
        try:
            query = """
            SELECT user_id, age, weight, height, biological_sex, email, updated_at
            FROM oura_personal_info
            ORDER BY updated_at DESC
            LIMIT 1
            """
            df = self._execute_query(query)
            if not df.empty:
                return df.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Failed to get personal info: {e}")
        return {}
    
    def get_daily_summary_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get daily summary data as DataFrame"""
        query = """
        SELECT 
            COALESCE(ds.date, s.date, a.date, r.date) as date,
            ds.overall_health_score,
            s.sleep_score,
            a.activity_score,
            a.steps,
            a.calories_total,
            a.total_active_minutes,
            r.readiness_score,
            r.temperature_deviation,
            r.hrv_balance,
            r.resting_heart_rate,
            st.stress_high_minutes,
            st.recovery_high_minutes,
            st.stress_recovery_ratio
        FROM oura_daily_summaries ds
        FULL OUTER JOIN oura_daily_sleep s ON ds.date = s.date
        FULL OUTER JOIN oura_activity a ON ds.date = a.date
        FULL OUTER JOIN oura_readiness r ON ds.date = r.date
        LEFT JOIN oura_stress st ON ds.date = st.date
        WHERE COALESCE(ds.date, s.date, a.date, r.date) BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate overall health score if missing
            if 'overall_health_score' not in df.columns or df['overall_health_score'].isna().all():
                score_cols = ['sleep_score', 'activity_score', 'readiness_score']
                existing_cols = [col for col in score_cols if col in df.columns]
                if existing_cols:
                    df['overall_health_score'] = df[existing_cols].mean(axis=1)
        
        return df
    
    def get_sleep_periods_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get detailed sleep period data"""
        query = """
        SELECT 
            date, type, total_sleep_hours, time_in_bed_hours,
            efficiency_percent, rem_hours, deep_hours, light_hours,
            awake_time, rem_percentage, deep_percentage, light_percentage,
            latency_minutes, heart_rate_avg, hrv_avg, respiratory_rate
        FROM oura_sleep_periods
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_activity_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get activity data"""
        query = """
        SELECT 
            date, activity_score, steps, distance_km,
            calories_active, calories_total,
            high_activity_minutes, medium_activity_minutes,
            low_activity_minutes, sedentary_minutes,
            total_active_minutes, met_minutes, inactivity_alerts,
            non_wear_minutes, resting_time_minutes
        FROM oura_activity
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # Add default values for missing columns
            if 'non_wear_minutes' not in df.columns:
                df['non_wear_minutes'] = 0
            if 'resting_time_minutes' not in df.columns:
                df['resting_time_minutes'] = 0
        return df
    
    def get_readiness_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get readiness data"""
        query = """
        SELECT 
            date, readiness_score, temperature_deviation,
            temperature_trend_deviation, recovery_index,
            resting_heart_rate, hrv_balance,
            score_activity_balance, score_body_temperature,
            score_hrv_balance, score_previous_night,
            score_recovery_index, score_resting_heart_rate,
            score_previous_day_activity, score_sleep_balance
        FROM oura_readiness
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # Add default values for missing score columns
            score_columns = [
                'score_activity_balance', 'score_body_temperature',
                'score_hrv_balance', 'score_previous_night',
                'score_recovery_index', 'score_resting_heart_rate',
                'score_previous_day_activity', 'score_sleep_balance'
            ]
            for col in score_columns:
                if col not in df.columns:
                    df[col] = None
        return df
    
    def get_workouts_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get workout data"""
        query = """
        SELECT 
            date, activity, intensity, duration_minutes,
            calories, distance_km, source, label
        FROM oura_workouts
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_stress_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get stress data"""
        query = """
        SELECT 
            date, stress_high_minutes, recovery_high_minutes,
            stress_recovery_ratio, day_summary
        FROM oura_stress
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_sleep_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get sleep trends for the last N days"""
        query = """
        WITH sleep_stats AS (
            SELECT 
                AVG(total_sleep_hours) as avg_sleep_hours,
                AVG(efficiency_percent) as avg_efficiency,
                AVG(rem_percentage) as avg_rem_percent,
                AVG(deep_percentage) as avg_deep_percent,
                AVG(light_percentage) as avg_light_percent,
                AVG(hrv_avg) as avg_hrv,
                AVG(heart_rate_avg) as avg_heart_rate
            FROM oura_sleep_periods
            WHERE date >= CURRENT_DATE - INTERVAL ':days days'
                AND type = 'long_sleep'
        )
        SELECT * FROM sleep_stats
        """
        
        df = self._execute_query(query.replace(':days', str(days)))
        if not df.empty:
            result = df.iloc[0].to_dict()
            # Add trend calculations here if needed
            return result
        return {}
    
    def get_activity_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get activity trends for the last N days"""
        query = """
        WITH activity_stats AS (
            SELECT 
                AVG(steps) as avg_steps,
                AVG(total_active_minutes) as avg_active_minutes,
                AVG(calories_total) as avg_calories,
                SUM(distance_km) as total_distance_km,
                AVG(activity_score) as avg_activity_score,
                COUNT(CASE WHEN steps >= 10000 THEN 1 END) as days_above_10k_steps,
                AVG(sedentary_minutes) / (24 * 60) * 100 as sedentary_percentage
            FROM oura_activity
            WHERE date >= CURRENT_DATE - INTERVAL ':days days'
        )
        SELECT * FROM activity_stats
        """
        
        df = self._execute_query(query.replace(':days', str(days)))
        if not df.empty:
            return df.iloc[0].to_dict()
        return {}
    
    def get_health_correlations(self, days: int = 30) -> pd.DataFrame:
        """Calculate correlations between health metrics"""
        query = """
        SELECT 
            s.sleep_score,
            a.activity_score,
            r.readiness_score,
            a.steps,
            a.total_active_minutes,
            r.hrv_balance,
            r.resting_heart_rate,
            r.temperature_deviation
        FROM oura_daily_sleep s
        JOIN oura_activity a ON s.date = a.date
        JOIN oura_readiness r ON s.date = r.date
        WHERE s.date >= CURRENT_DATE - INTERVAL ':days days'
        """
        
        df = self._execute_query(query.replace(':days', str(days)))
        if not df.empty:
            return df.corr()
        return pd.DataFrame()
    
    def get_weekly_summary(self, weeks: int = 4) -> pd.DataFrame:
        """Get weekly summary statistics"""
        query = """
        SELECT 
            DATE_TRUNC('week', s.date)::date as week_start,
            AVG(s.sleep_score) as sleep_score,
            AVG(a.activity_score) as activity_score,
            AVG(r.readiness_score) as readiness_score,
            AVG(COALESCE(ds.overall_health_score, 
                (s.sleep_score + a.activity_score + r.readiness_score) / 3.0)) as overall_health_score,
            AVG(a.steps) as steps,
            AVG(a.total_active_minutes) as total_active_minutes,
            AVG(r.hrv_balance) as hrv_balance,
            AVG(r.resting_heart_rate) as resting_heart_rate
        FROM oura_daily_sleep s
        JOIN oura_activity a ON s.date = a.date
        JOIN oura_readiness r ON s.date = r.date
        LEFT JOIN oura_daily_summaries ds ON s.date = ds.date
        WHERE s.date >= CURRENT_DATE - INTERVAL ':weeks weeks'
        GROUP BY DATE_TRUNC('week', s.date)
        ORDER BY week_start
        """
        
        df = self._execute_query(query.replace(':weeks', str(weeks)))
        if not df.empty:
            df['week_start'] = pd.to_datetime(df['week_start'])
        return df
    
    def _calculate_trend(self, df: pd.DataFrame, column: str) -> str:
        """Calculate trend direction for a metric"""
        # Simple trend calculation - can be enhanced
        if len(df) < 3:
            return 'insufficient_data'
        
        recent_avg = df[column].tail(7).mean()
        older_avg = df[column].head(7).mean()
        
        if recent_avg > older_avg * 1.05:
            return 'increasing'
        elif recent_avg < older_avg * 0.95:
            return 'decreasing'
        else:
            return 'stable'
    

    def get_heart_rate_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get daily heart rate data from sleep periods and readiness tables
        
        Since continuous heart rate monitoring is not available, we use:
        - Sleep heart rate data (average and min) from sleep periods
        - Resting heart rate from readiness data
        - HRV metrics from sleep periods
        """
        
        query = """
        SELECT 
            COALESCE(sp.date, r.date) as date,
            r.resting_heart_rate as resting_hr,
            sp.heart_rate_min as min_hr,
            sp.heart_rate_avg as avg_hr,
            -- Estimate max HR as avg + 20% since we don't have actual max
            CASE 
                WHEN sp.heart_rate_avg IS NOT NULL 
                THEN sp.heart_rate_avg * 1.2 
                ELSE NULL 
            END as max_hr,
            sp.hrv_avg as hrv_avg,
            sp.hrv_max as hrv_max,
            sp.hrv_min as hrv_min,
            sp.hrv_stdev as hr_variability,
            sp.respiratory_rate
        FROM oura_readiness r
        FULL OUTER JOIN (
            SELECT 
                date,
                AVG(heart_rate_avg) as heart_rate_avg,
                MIN(heart_rate_min) as heart_rate_min,
                AVG(hrv_avg) as hrv_avg,
                MAX(hrv_max) as hrv_max,
                MIN(hrv_min) as hrv_min,
                AVG(hrv_stdev) as hrv_stdev,
                AVG(respiratory_rate) as respiratory_rate
            FROM oura_sleep_periods
            WHERE type = 'long_sleep'  -- Focus on main sleep periods
            GROUP BY date
        ) sp ON r.date = sp.date
        WHERE COALESCE(sp.date, r.date) BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            
            # Fill missing values with reasonable defaults
            if 'resting_hr' not in df.columns:
                df['resting_hr'] = None
            if 'min_hr' not in df.columns:
                df['min_hr'] = df['resting_hr']  # Use resting HR as minimum if not available
            if 'max_hr' not in df.columns:
                df['max_hr'] = None
            if 'hr_variability' not in df.columns:
                df['hr_variability'] = 0
                
        return df
    
    def get_vo2_max_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get VO2 Max data"""
        query = """
        SELECT 
            date,
            vo2_max,
            raw_data
        FROM oura_vo2_max
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_cardiovascular_age_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get Cardiovascular Age data"""
        query = """
        SELECT 
            date,
            cardiovascular_age,
            raw_data
        FROM oura_cardiovascular_age
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_resilience_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get Resilience data"""
        query = """
        SELECT 
            date,
            resilience_level,
            raw_data
        FROM oura_resilience
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_spo2_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get SpO2 (blood oxygen) data"""
        query = """
        SELECT 
            date,
            spo2_percentage_avg,
            breathing_disturbance_index,
            raw_data
        FROM oura_spo2
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # Extract average SpO2 from raw_data if not in dedicated column
            if 'spo2_percentage_avg' not in df.columns and 'raw_data' in df.columns:
                import json
                def extract_spo2(raw):
                    try:
                        data = json.loads(raw) if isinstance(raw, str) else raw
                        return data.get('spo2_percentage', {}).get('average')
                    except:
                        return None
                df['spo2_percentage_avg'] = df['raw_data'].apply(extract_spo2)
        return df
    
    def get_sessions_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get meditation/breathing sessions data"""
        query = """
        SELECT 
            date,
            type,
            duration_minutes,
            mood_start,
            mood_end,
            raw_data
        FROM oura_sessions
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_tags_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get enhanced tags data"""
        query = """
        SELECT 
            date,
            tag_type,
            tags,
            raw_data
        FROM oura_tags
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_sleep_time_recommendations_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get sleep time recommendations"""
        query = """
        SELECT 
            date,
            recommendation,
            raw_data
        FROM oura_sleep_time
        WHERE date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_rest_mode_periods_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get rest mode periods data"""
        query = """
        SELECT 
            start_date,
            end_date,
            rest_mode_state,
            raw_data
        FROM oura_rest_mode_periods
        WHERE start_date <= :end_date AND (end_date >= :start_date OR end_date IS NULL)
        ORDER BY start_date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['start_date'] = pd.to_datetime(df['start_date'])
            df['end_date'] = pd.to_datetime(df['end_date'])
        return df
    
    def get_ring_configuration_df(self) -> pd.DataFrame:
        """Get ring configuration data"""
        query = """
        SELECT 
            id,
            color,
            design,
            firmware_version,
            hardware_type,
            set_up_at,
            size,
            raw_data
        FROM oura_ring_configuration
        ORDER BY set_up_at DESC
        """
        
        df = self._execute_query(query)
        if not df.empty and 'set_up_at' in df.columns:
            df['set_up_at'] = pd.to_datetime(df['set_up_at'])
        return df
    
    def get_enhanced_daily_summary_df(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get enhanced daily summary with all new metrics"""
        query = """
        SELECT 
            COALESCE(ds.date, s.date, a.date, r.date) as date,
            ds.overall_health_score,
            s.sleep_score,
            a.activity_score,
            a.steps,
            a.calories_total,
            a.total_active_minutes,
            r.readiness_score,
            r.temperature_deviation,
            r.hrv_balance,
            r.resting_heart_rate,
            st.stress_high_minutes,
            st.recovery_high_minutes,
            st.stress_recovery_ratio,
            v.vo2_max,
            ca.cardiovascular_age,
            res.resilience_level,
            spo2.spo2_percentage_avg,
            spo2.breathing_disturbance_index
        FROM oura_daily_summaries ds
        FULL OUTER JOIN oura_daily_sleep s ON ds.date = s.date
        FULL OUTER JOIN oura_activity a ON ds.date = a.date
        FULL OUTER JOIN oura_readiness r ON ds.date = r.date
        LEFT JOIN oura_stress st ON ds.date = st.date
        LEFT JOIN oura_vo2_max v ON ds.date = v.date
        LEFT JOIN oura_cardiovascular_age ca ON ds.date = ca.date
        LEFT JOIN oura_resilience res ON ds.date = res.date
        LEFT JOIN oura_spo2 spo2 ON ds.date = spo2.date
        WHERE COALESCE(ds.date, s.date, a.date, r.date) BETWEEN :start_date AND :end_date
        ORDER BY date
        """
        
        df = self._execute_query(query, {'start_date': start_date, 'end_date': end_date})
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate overall health score if missing
            if 'overall_health_score' not in df.columns or df['overall_health_score'].isna().all():
                score_cols = ['sleep_score', 'activity_score', 'readiness_score']
                existing_cols = [col for col in score_cols if col in df.columns]
                if existing_cols:
                    df['overall_health_score'] = df[existing_cols].mean(axis=1)
        
        return df



    def close(self):
        """Close database connections"""
        self.engine.dispose()
