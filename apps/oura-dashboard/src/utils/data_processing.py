"""
Data processing utilities for Oura Health Dashboard
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_overall_health_score(df):
    """Calculate overall health score from component scores"""
    score_cols = ['sleep_score', 'activity_score', 'readiness_score']
    existing_cols = [col for col in score_cols if col in df.columns]
    
    if existing_cols:
        df['overall_health_score'] = df[existing_cols].mean(axis=1)
    
    return df

def add_day_of_week(df, date_column='date'):
    """Add day of week column to dataframe"""
    df['day_of_week'] = pd.to_datetime(df[date_column]).dt.day_name()
    df['day_of_week_num'] = pd.to_datetime(df[date_column]).dt.dayofweek
    return df

def calculate_moving_average(df, column, window=7):
    """Calculate moving average for a column"""
    df[f'{column}_ma{window}'] = df[column].rolling(window=window, min_periods=1).mean()
    return df

def calculate_sleep_consistency(df_sleep):
    """Calculate sleep consistency metrics"""
    # Filter for main sleep only
    df_main = df_sleep[df_sleep['type'] == 'long_sleep'].copy()
    
    consistency_metrics = {
        'sleep_duration_std': df_main['total_sleep_hours'].std(),
        'bedtime_consistency': calculate_bedtime_consistency(df_main),
        'efficiency_consistency': df_main['efficiency_percent'].std()
    }
    
    return consistency_metrics

def calculate_bedtime_consistency(df_sleep):
    """Calculate bedtime consistency score"""
    # This is a simplified calculation
    # In reality, you'd need actual bedtime data
    return 85.0  # Placeholder

def filter_outliers(df, column, method='iqr', threshold=1.5):
    """Filter outliers from a dataframe column"""
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    elif method == 'zscore':
        z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
        return df[z_scores < threshold]
    else:
        return df

def calculate_activity_trends(df_activity, window=7):
    """Calculate activity trends and patterns"""
    trends = {}
    
    # Steps trend
    recent_steps = df_activity['steps'].tail(window).mean()
    older_steps = df_activity['steps'].head(window).mean()
    
    if recent_steps > older_steps * 1.05:
        trends['steps_trend'] = 'increasing'
    elif recent_steps < older_steps * 0.95:
        trends['steps_trend'] = 'decreasing'
    else:
        trends['steps_trend'] = 'stable'
    
    # Activity score trend
    if 'activity_score' in df_activity.columns:
        recent_score = df_activity['activity_score'].tail(window).mean()
        older_score = df_activity['activity_score'].head(window).mean()
        trends['activity_score_change'] = recent_score - older_score
    
    # Days meeting step goal
    trends['days_meeting_10k'] = len(df_activity[df_activity['steps'] >= 10000])
    trends['percent_days_10k'] = trends['days_meeting_10k'] / len(df_activity) * 100
    
    return trends

def calculate_recovery_score(df_readiness):
    """Calculate composite recovery score"""
    # Weighted average of recovery-related metrics
    weights = {
        'readiness_score': 0.4,
        'score_recovery_index': 0.3,
        'score_hrv_balance': 0.3
    }
    
    recovery_score = 0
    total_weight = 0
    
    for col, weight in weights.items():
        if col in df_readiness.columns:
            score_contrib = df_readiness[col].mean() * weight
            if not pd.isna(score_contrib):
                recovery_score += score_contrib
                total_weight += weight
    
    if total_weight > 0:
        recovery_score = recovery_score / total_weight
    
    return recovery_score

def get_date_range_summary(df, date_col='date'):
    """Get summary statistics for a date range"""
    summary = {
        'start_date': df[date_col].min(),
        'end_date': df[date_col].max(),
        'total_days': len(df[date_col].unique()),
        'missing_days': calculate_missing_days(df[date_col])
    }
    return summary

def calculate_missing_days(date_series):
    """Calculate number of missing days in date series"""
    date_series = pd.to_datetime(date_series)
    date_range = pd.date_range(start=date_series.min(), end=date_series.max())
    missing_days = len(date_range) - len(date_series.unique())
    return missing_days

def aggregate_by_period(df, period='W', date_col='date', agg_dict=None):
    """Aggregate data by time period (W, M, Q)"""
    df[date_col] = pd.to_datetime(df[date_col])
    df_period = df.set_index(date_col)
    
    if agg_dict is None:
        # Default aggregation: mean for numeric columns
        numeric_cols = df_period.select_dtypes(include=[np.number]).columns
        agg_dict = {col: 'mean' for col in numeric_cols}
    
    return df_period.resample(period).agg(agg_dict).reset_index()

def calculate_percentile_rank(value, series):
    """Calculate percentile rank of a value in a series"""
    return (series < value).sum() / len(series) * 100

def format_duration(minutes):
    """Format duration in minutes to readable string"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"

def calculate_sleep_debt(df_sleep, target_hours=8):
    """Calculate cumulative sleep debt"""
    df_main = df_sleep[df_sleep['type'] == 'long_sleep'].copy()
    df_main['sleep_debt'] = target_hours - df_main['total_sleep_hours']
    df_main['cumulative_debt'] = df_main['sleep_debt'].cumsum()
    return df_main

def calculate_sleep_quality_score(df_sleep):
    """Calculate overall sleep quality score."""
    # Weighted components
    weights = {
        "efficiency": 0.3,
        "deep_sleep": 0.2,
        "rem_sleep": 0.2,
        "duration": 0.2,
        "latency": 0.1,
    }

    score = 0

    # Efficiency component (target: 85%+)
    avg_efficiency = df_sleep["efficiency_percent"].mean()
    efficiency_score = min(100, (avg_efficiency / 85) * 100)
    score += efficiency_score * weights["efficiency"]

    # Deep sleep component (target: 15-20%)
    avg_deep = df_sleep["deep_percentage"].mean()
    deep_score = (
        min(100, (avg_deep / 15) * 100)
        if avg_deep < 20
        else max(0, 100 - (avg_deep - 20) * 5)
    )
    score += deep_score * weights["deep_sleep"]

    # REM sleep component (target: 20-25%)
    avg_rem = df_sleep["rem_percentage"].mean()
    rem_score = (
        min(100, (avg_rem / 20) * 100)
        if avg_rem < 25
        else max(0, 100 - (avg_rem - 25) * 4)
    )
    score += rem_score * weights["rem_sleep"]

    # Duration component (target: 7-9 hours)
    avg_duration = df_sleep["total_sleep_hours"].mean()
    if 7 <= avg_duration <= 9:
        duration_score = 100
    elif avg_duration < 7:
        duration_score = (avg_duration / 7) * 100
    else:
        duration_score = max(0, 100 - (avg_duration - 9) * 20)
    score += duration_score * weights["duration"]

    # Latency component (target: <20 min)
    avg_latency = df_sleep["latency_minutes"].mean()
    latency_score = (
        max(0, 100 - (avg_latency / 20) * 50) if avg_latency < 40 else 0
    )
    score += latency_score * weights["latency"]

    return score

def identify_patterns(df, metric_col, threshold_pct=20):
    """Identify patterns in metrics (improving, declining, stable)"""
    if len(df) < 7:
        return "insufficient_data"
    
    # Compare recent week to previous week
    recent_avg = df[metric_col].tail(7).mean()
    previous_avg = df[metric_col].iloc[-14:-7].mean()
    
    pct_change = ((recent_avg - previous_avg) / previous_avg) * 100
    
    if pct_change > threshold_pct:
        return "significant_improvement"
    elif pct_change > 5:
        return "improving"
    elif pct_change < -threshold_pct:
        return "significant_decline"
    elif pct_change < -5:
        return "declining"
    else:
        return "stable"