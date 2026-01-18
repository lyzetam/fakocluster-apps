"""Async database queries for Oura Health Agent.

Provides query methods for all 19 Oura data tables.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from database.connection import get_engine

logger = logging.getLogger(__name__)


class OuraDataQueries:
    """Async query interface for Oura health data."""

    def __init__(self, connection_string: str):
        """Initialize with database connection string.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self._engine: AsyncEngine | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine, creating it if needed."""
        if self._engine is None:
            self._engine = get_engine(self.connection_string)
        return self._engine

    async def _execute_query(
        self, query: str, params: dict | None = None
    ) -> pd.DataFrame:
        """Execute a query and return results as DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            pd.DataFrame: Query results
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text(query), params or {})
                rows = result.fetchall()
                columns = result.keys()
                return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def _execute_query_one(
        self, query: str, params: dict | None = None
    ) -> dict[str, Any] | None:
        """Execute a query and return first row as dict.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            dict or None: First row as dictionary
        """
        df = await self._execute_query(query, params)
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    # ==================== Sleep Queries ====================

    async def get_last_night_sleep(self) -> dict[str, Any] | None:
        """Get the most recent sleep data."""
        query = """
        SELECT
            date, type, total_sleep_hours, time_in_bed_hours,
            efficiency_percent, rem_hours, deep_hours, light_hours,
            awake_time, rem_percentage, deep_percentage, light_percentage,
            latency_minutes, heart_rate_avg, heart_rate_min, hrv_avg,
            hrv_min, hrv_max, respiratory_rate
        FROM oura_sleep_periods
        WHERE type = 'long_sleep'
        ORDER BY date DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    async def get_sleep_by_date(self, target_date: date) -> dict[str, Any] | None:
        """Get sleep data for a specific date."""
        query = """
        SELECT
            date, type, total_sleep_hours, time_in_bed_hours,
            efficiency_percent, rem_hours, deep_hours, light_hours,
            awake_time, rem_percentage, deep_percentage, light_percentage,
            latency_minutes, heart_rate_avg, heart_rate_min, hrv_avg,
            hrv_min, hrv_max, respiratory_rate
        FROM oura_sleep_periods
        WHERE date = :target_date AND type = 'long_sleep'
        LIMIT 1
        """
        return await self._execute_query_one(query, {"target_date": target_date})

    async def get_sleep_trends(self, days: int = 7) -> pd.DataFrame:
        """Get sleep data for the last N days."""
        query = """
        SELECT
            date, total_sleep_hours, time_in_bed_hours,
            efficiency_percent, rem_hours, deep_hours, light_hours,
            rem_percentage, deep_percentage, light_percentage,
            latency_minutes, heart_rate_avg, hrv_avg, respiratory_rate
        FROM oura_sleep_periods
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
            AND type = 'long_sleep'
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_daily_sleep_scores(self, days: int = 7) -> pd.DataFrame:
        """Get daily sleep scores."""
        query = """
        SELECT
            date, sleep_score,
            score_total_sleep, score_efficiency, score_restfulness,
            score_rem_sleep, score_deep_sleep, score_latency, score_timing
        FROM oura_daily_sleep
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_sleep_time_recommendation(self) -> dict[str, Any] | None:
        """Get the latest sleep time recommendation."""
        query = """
        SELECT date, recommendation
        FROM oura_sleep_time
        ORDER BY date DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    # ==================== Activity Queries ====================

    async def get_today_activity(self) -> dict[str, Any] | None:
        """Get today's activity data."""
        query = """
        SELECT
            date, activity_score, steps, distance_km,
            calories_active, calories_total,
            high_activity_minutes, medium_activity_minutes,
            low_activity_minutes, sedentary_minutes,
            total_active_minutes, met_minutes, inactivity_alerts
        FROM oura_activity
        WHERE date = CURRENT_DATE
        LIMIT 1
        """
        result = await self._execute_query_one(query)
        if result is None:
            # Try yesterday if today not available
            query = query.replace("= CURRENT_DATE", "= CURRENT_DATE - 1")
            result = await self._execute_query_one(query)
        return result

    async def get_activity_trends(self, days: int = 7) -> pd.DataFrame:
        """Get activity data for the last N days."""
        query = """
        SELECT
            date, activity_score, steps, distance_km,
            calories_active, calories_total,
            high_activity_minutes, medium_activity_minutes,
            low_activity_minutes, sedentary_minutes,
            total_active_minutes, met_minutes, inactivity_alerts
        FROM oura_activity
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_activity_stats(self, days: int = 30) -> dict[str, Any] | None:
        """Get aggregated activity statistics."""
        query = """
        SELECT
            AVG(steps) as avg_steps,
            AVG(total_active_minutes) as avg_active_minutes,
            AVG(calories_total) as avg_calories,
            SUM(distance_km) as total_distance_km,
            AVG(activity_score) as avg_activity_score,
            COUNT(CASE WHEN steps >= 10000 THEN 1 END) as days_above_10k_steps,
            COUNT(*) as total_days
        FROM oura_activity
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        """
        return await self._execute_query_one(query, {"days_interval": f"{days} days"})

    # ==================== Workout Queries ====================

    async def get_recent_workouts(self, days: int = 7) -> pd.DataFrame:
        """Get recent workouts."""
        query = """
        SELECT
            date, activity, intensity, duration_minutes,
            calories, distance_km, source, label
        FROM oura_workouts
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date DESC
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_workout_summary(self, days: int = 30) -> dict[str, Any] | None:
        """Get workout summary statistics."""
        query = """
        SELECT
            COUNT(*) as workout_count,
            SUM(duration_minutes) as total_duration_minutes,
            SUM(calories) as total_calories,
            SUM(distance_km) as total_distance_km,
            AVG(duration_minutes) as avg_duration_minutes
        FROM oura_workouts
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        """
        return await self._execute_query_one(query, {"days_interval": f"{days} days"})

    async def get_workouts_by_type(self, activity_type: str, days: int = 90) -> pd.DataFrame:
        """Get workouts filtered by activity type."""
        query = """
        SELECT
            date, activity, intensity, duration_minutes,
            calories, distance_km, source, label
        FROM oura_workouts
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
            AND LOWER(activity) LIKE LOWER(:activity_type)
        ORDER BY date DESC
        """
        return await self._execute_query(
            query, {"days_interval": f"{days} days", "activity_type": f"%{activity_type}%"}
        )

    # ==================== Readiness Queries ====================

    async def get_latest_readiness(self) -> dict[str, Any] | None:
        """Get the most recent readiness data."""
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
        ORDER BY date DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    async def get_readiness_trends(self, days: int = 7) -> pd.DataFrame:
        """Get readiness data for the last N days."""
        query = """
        SELECT
            date, readiness_score, temperature_deviation,
            recovery_index, resting_heart_rate, hrv_balance,
            score_activity_balance, score_hrv_balance,
            score_previous_night, score_sleep_balance
        FROM oura_readiness
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    # ==================== Heart Rate & HRV Queries ====================

    async def get_hrv_analysis(self, days: int = 7) -> pd.DataFrame:
        """Get HRV data from sleep periods."""
        query = """
        SELECT
            date, hrv_avg, hrv_min, hrv_max,
            heart_rate_avg, heart_rate_min
        FROM oura_sleep_periods
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
            AND type = 'long_sleep'
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_resting_heart_rate(self, days: int = 7) -> pd.DataFrame:
        """Get resting heart rate from readiness data."""
        query = """
        SELECT
            date, resting_heart_rate, hrv_balance
        FROM oura_readiness
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    # ==================== Stress & Resilience Queries ====================

    async def get_stress_data(self, days: int = 7) -> pd.DataFrame:
        """Get stress data."""
        query = """
        SELECT
            date, stress_high_minutes, recovery_high_minutes,
            stress_recovery_ratio, day_summary
        FROM oura_stress
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_resilience_data(self, days: int = 30) -> pd.DataFrame:
        """Get resilience data."""
        query = """
        SELECT
            date, level, sleep_recovery, daytime_recovery,
            raw_data
        FROM oura_resilience
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_latest_resilience(self) -> dict[str, Any] | None:
        """Get the most recent resilience data."""
        query = """
        SELECT
            date, level, sleep_recovery, daytime_recovery
        FROM oura_resilience
        ORDER BY date DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    # ==================== Advanced Metrics Queries ====================

    async def get_vo2_max(self, days: int = 30) -> pd.DataFrame:
        """Get VO2 max data."""
        query = """
        SELECT date, vo2_max
        FROM oura_vo2_max
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_cardiovascular_age(self, days: int = 30) -> pd.DataFrame:
        """Get cardiovascular age data."""
        query = """
        SELECT date, cardiovascular_age
        FROM oura_cardiovascular_age
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_spo2_data(self, days: int = 7) -> pd.DataFrame:
        """Get SpO2 (blood oxygen) data."""
        query = """
        SELECT
            date, spo2_percentage_avg, breathing_disturbance_index
        FROM oura_spo2
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    # ==================== Sessions Queries ====================

    async def get_sessions(self, days: int = 30) -> pd.DataFrame:
        """Get meditation and breathing sessions."""
        query = """
        SELECT
            date, type, mood, start_datetime, end_datetime,
            heart_rate, heart_rate_variability, motion_count
        FROM oura_sessions
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date DESC
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    # ==================== Summary & Trends Queries ====================

    async def get_daily_summaries(self, days: int = 7) -> pd.DataFrame:
        """Get daily summary data."""
        query = """
        SELECT
            COALESCE(ds.date, s.date, a.date, r.date) as date,
            ds.overall_health_score,
            s.sleep_score,
            a.activity_score,
            a.steps,
            r.readiness_score,
            r.hrv_balance,
            r.resting_heart_rate,
            r.temperature_deviation
        FROM oura_daily_summaries ds
        FULL OUTER JOIN oura_daily_sleep s ON ds.date = s.date
        FULL OUTER JOIN oura_activity a ON ds.date = a.date
        FULL OUTER JOIN oura_readiness r ON ds.date = r.date
        WHERE COALESCE(ds.date, s.date, a.date, r.date) >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_weekly_summary(self, weeks: int = 4) -> pd.DataFrame:
        """Get weekly summary statistics."""
        query = """
        SELECT
            DATE_TRUNC('week', s.date)::date as week_start,
            AVG(s.sleep_score) as sleep_score,
            AVG(a.activity_score) as activity_score,
            AVG(r.readiness_score) as readiness_score,
            AVG(a.steps) as avg_steps,
            AVG(a.total_active_minutes) as avg_active_minutes,
            AVG(r.hrv_balance) as avg_hrv_balance,
            AVG(r.resting_heart_rate) as avg_resting_hr
        FROM oura_daily_sleep s
        JOIN oura_activity a ON s.date = a.date
        JOIN oura_readiness r ON s.date = r.date
        WHERE s.date >= CURRENT_DATE - INTERVAL :weeks_interval
        GROUP BY DATE_TRUNC('week', s.date)
        ORDER BY week_start
        """
        return await self._execute_query(query, {"weeks_interval": f"{weeks} weeks"})

    async def get_health_correlations(self, days: int = 30) -> pd.DataFrame:
        """Get data for correlation analysis."""
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
        WHERE s.date >= CURRENT_DATE - INTERVAL :days_interval
        """
        df = await self._execute_query(query, {"days_interval": f"{days} days"})
        if not df.empty:
            return df.corr()
        return pd.DataFrame()

    # ==================== Utility Queries ====================

    async def get_personal_info(self) -> dict[str, Any] | None:
        """Get personal information."""
        query = """
        SELECT user_id, age, weight, height, biological_sex, email
        FROM oura_personal_info
        ORDER BY updated_at DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    async def get_ring_configuration(self) -> dict[str, Any] | None:
        """Get ring configuration."""
        query = """
        SELECT ring_id, color, design, firmware_version, size, set_up_at
        FROM oura_ring_configuration
        ORDER BY set_up_at DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    async def get_rest_mode_periods(self, days: int = 90) -> pd.DataFrame:
        """Get rest mode periods."""
        query = """
        SELECT
            start_date, end_date
        FROM oura_rest_mode_periods
        WHERE start_date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY start_date DESC
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_tags(self, days: int = 30) -> pd.DataFrame:
        """Get user tags."""
        query = """
        SELECT
            date, tag_type, tags
        FROM oura_tags
        WHERE date >= CURRENT_DATE - INTERVAL :days_interval
        ORDER BY date DESC
        """
        return await self._execute_query(query, {"days_interval": f"{days} days"})

    async def get_collection_status(self) -> dict[str, Any] | None:
        """Get the most recent data collection status."""
        query = """
        SELECT
            collection_time, start_date, end_date,
            results, status
        FROM oura_collection_logs
        ORDER BY collection_time DESC
        LIMIT 1
        """
        return await self._execute_query_one(query)

    async def get_date_range(self) -> tuple[date, date]:
        """Get the date range of available data."""
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
        result = await self._execute_query_one(query)
        if result:
            return result["min_date"], result["max_date"]
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date
