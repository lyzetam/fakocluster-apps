"""
Metrics components for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
from ui_config import METRIC_ICONS, STATUS_ICONS

def render_metric_card(title, value, delta=None, icon=None, metric_type="default"):
    """
    Render a styled metric card
    
    Args:
        title: Metric title
        value: Metric value
        delta: Change from baseline (optional)
        icon: Icon to display (optional)
        metric_type: Type of metric for styling (sleep, activity, readiness, overall)
    """
    if icon:
        title = f"{icon} {title}"
    
    st.metric(
        label=title,
        value=value,
        delta=delta
    )

def render_health_score_metrics(df_summary):
    """Render the main health score metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_health = df_summary['overall_health_score'].mean()
        if pd.notna(avg_health):
            render_metric_card(
                "Avg Health Score",
                f"{avg_health:.0f}",
                f"{avg_health - 75:.1f}" if avg_health else None,
                icon="💚",
                metric_type="overall"
            )
    
    with col2:
        avg_sleep = df_summary['sleep_score'].mean()
        if pd.notna(avg_sleep):
            render_metric_card(
                "Avg Sleep Score",
                f"{avg_sleep:.0f}",
                f"{avg_sleep - 75:.1f}" if avg_sleep else None,
                icon="🌙",
                metric_type="sleep"
            )
    
    with col3:
        avg_activity = df_summary['activity_score'].mean()
        if pd.notna(avg_activity):
            render_metric_card(
                "Avg Activity Score",
                f"{avg_activity:.0f}",
                f"{avg_activity - 75:.1f}" if avg_activity else None,
                icon="🏃",
                metric_type="activity"
            )
    
    with col4:
        avg_readiness = df_summary['readiness_score'].mean()
        if pd.notna(avg_readiness):
            render_metric_card(
                "Avg Readiness Score",
                f"{avg_readiness:.0f}",
                f"{avg_readiness - 75:.1f}" if avg_readiness else None,
                icon="💪",
                metric_type="readiness"
            )

def render_sleep_metrics(df_sleep):
    """Render sleep-specific metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    # Filter for main sleep only
    df_main_sleep = df_sleep[df_sleep['type'] == 'long_sleep']
    
    with col1:
        avg_sleep = df_main_sleep['total_sleep_hours'].mean()
        st.metric("Avg Sleep Duration", f"{avg_sleep:.1f}h")
    
    with col2:
        avg_efficiency = df_main_sleep['efficiency_percent'].mean()
        st.metric("Avg Sleep Efficiency", f"{avg_efficiency:.0f}%")
    
    with col3:
        avg_hrv = df_main_sleep['hrv_avg'].mean()
        if pd.notna(avg_hrv):
            st.metric("Avg HRV", f"{avg_hrv:.0f}")
    
    with col4:
        avg_hr = df_main_sleep['heart_rate_avg'].mean()
        if pd.notna(avg_hr):
            st.metric("Avg Heart Rate", f"{avg_hr:.0f} bpm")

def render_activity_metrics(df_activity):
    """Render activity-specific metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_steps = df_activity['steps'].mean()
        st.metric("Avg Daily Steps", f"{avg_steps:,.0f}")
    
    with col2:
        total_distance = df_activity['distance_km'].sum()
        st.metric("Total Distance", f"{total_distance:.1f} km")
    
    with col3:
        avg_active = df_activity['total_active_minutes'].mean()
        st.metric("Avg Active Minutes", f"{avg_active:.0f}")
    
    with col4:
        avg_calories = df_activity['calories_total'].mean()
        st.metric("Avg Daily Calories", f"{avg_calories:,.0f}")

def render_readiness_metrics(df_readiness, df_stress=None):
    """Render readiness and recovery metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_readiness = df_readiness['readiness_score'].mean()
        st.metric("Avg Readiness", f"{avg_readiness:.0f}")
    
    with col2:
        avg_hr = df_readiness['resting_heart_rate'].mean()
        if pd.notna(avg_hr):
            st.metric("Avg Resting HR", f"{avg_hr:.0f} bpm")
    
    with col3:
        avg_hrv_balance = df_readiness['hrv_balance'].mean()
        if pd.notna(avg_hrv_balance):
            st.metric("Avg HRV Balance", f"{avg_hrv_balance:.0f}")
    
    with col4:
        if df_stress is not None and not df_stress.empty:
            avg_stress_ratio = df_stress['stress_recovery_ratio'].mean()
            if pd.notna(avg_stress_ratio):
                st.metric("Avg Stress Ratio", f"{avg_stress_ratio:.2f}")

def render_workout_metrics(df_workouts):
    """Render workout summary metrics"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_workouts = len(df_workouts)
        st.metric("Total Workouts", total_workouts)
    
    with col2:
        total_duration = df_workouts['duration_minutes'].sum()
        st.metric("Total Duration", f"{total_duration:.0f} min")
    
    with col3:
        total_calories = df_workouts['calories'].sum()
        st.metric("Calories Burned", f"{total_calories:,.0f}")

def get_score_status(score):
    """Get status and color for a score"""
    if score >= 85:
        return "Excellent", "green", STATUS_ICONS['good']
    elif score >= 70:
        return "Good", "orange", STATUS_ICONS['warning']
    else:
        return "Needs Attention", "red", STATUS_ICONS['error']

def render_score_gauge(score, title, target=75):
    """Render a gauge-style metric for scores"""
    status, color, icon = get_score_status(score)
    
    delta = score - target
    delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
    
    st.metric(
        label=f"{title} {icon}",
        value=f"{score:.0f}",
        delta=f"{delta_str} vs target"
    )