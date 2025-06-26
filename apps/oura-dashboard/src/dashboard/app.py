"""
Oura Health Dashboard - Main Application
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import os
from typing import Dict, Any
import numpy as np

# Import custom queries
from queries import OuraDataQueries

# Page configuration
st.set_page_config(
    page_title="Oura Health Dashboard",
    page_icon="💍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size: 18px !important;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'queries' not in st.session_state:
    try:
        # Import config to get database connection
        from config import get_database_connection_string
        connection_string = get_database_connection_string()
        st.session_state.queries = OuraDataQueries(connection_string)
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()

# Sidebar
st.sidebar.title("💍 Oura Health Dashboard")
st.sidebar.markdown("---")


# Date range selection
min_date, max_date = st.session_state.queries.get_date_range()
st.sidebar.subheader("Date Range")

# Calculate default start date (30 days ago or min_date, whichever is later)
default_start = max(max_date - timedelta(days=30), min_date)

start_date = st.sidebar.date_input(
    "Start Date",
    value=default_start,  # Changed from max_date - timedelta(days=30)
    min_value=min_date,
    max_value=max_date
)
end_date = st.sidebar.date_input(
    "End Date",
    value=max_date,
    min_value=start_date,
    max_value=max_date
)

# Personal info
personal_info = st.session_state.queries.get_personal_info()
if personal_info:
    st.sidebar.subheader("Personal Info")
    if personal_info.get('age'):
        st.sidebar.text(f"Age: {personal_info['age']}")
    if personal_info.get('height') and personal_info.get('weight'):
        bmi = personal_info['weight'] / ((personal_info['height']/100) ** 2)
        st.sidebar.text(f"BMI: {bmi:.1f}")

# Navigation
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Sleep Analysis", "Activity Tracking", "Readiness & Recovery", 
     "Trends & Insights", "Detailed Reports"]
)

# Main content
if page == "Overview":
    st.title("Health Overview Dashboard")
    st.markdown(f"**Date Range:** {start_date} to {end_date}")
    
    # Get summary data
    df_summary = st.session_state.queries.get_daily_summary_df(start_date, end_date)
    
    if not df_summary.empty:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_health = df_summary['overall_health_score'].mean()
            if pd.notna(avg_health):
                st.metric(
                    "Avg Health Score",
                    f"{avg_health:.0f}",
                    f"{avg_health - 75:.1f}" if avg_health else None
                )
        
        with col2:
            avg_sleep = df_summary['sleep_score'].mean()
            if pd.notna(avg_sleep):
                st.metric(
                    "Avg Sleep Score",
                    f"{avg_sleep:.0f}",
                    f"{avg_sleep - 75:.1f}" if avg_sleep else None
                )
        
        with col3:
            avg_activity = df_summary['activity_score'].mean()
            if pd.notna(avg_activity):
                st.metric(
                    "Avg Activity Score",
                    f"{avg_activity:.0f}",
                    f"{avg_activity - 75:.1f}" if avg_activity else None
                )
        
        with col4:
            avg_readiness = df_summary['readiness_score'].mean()
            if pd.notna(avg_readiness):
                st.metric(
                    "Avg Readiness Score",
                    f"{avg_readiness:.0f}",
                    f"{avg_readiness - 75:.1f}" if avg_readiness else None
                )
        
        st.markdown("---")
        
        # Overall health score trend
        st.subheader("Health Score Trends")
        
        # Create line chart with all scores
        fig = go.Figure()
        
        # Add traces for each score type
        score_columns = [
            ('overall_health_score', 'Overall Health', '#FF6B6B'),
            ('sleep_score', 'Sleep', '#4ECDC4'),
            ('activity_score', 'Activity', '#45B7D1'),
            ('readiness_score', 'Readiness', '#96CEB4')
        ]
        
        for col, name, color in score_columns:
            if col in df_summary.columns:
                fig.add_trace(go.Scatter(
                    x=df_summary['date'],
                    y=df_summary[col],
                    mode='lines+markers',
                    name=name,
                    line=dict(color=color, width=3),
                    marker=dict(size=6)
                ))
        
        fig.update_layout(
            title="Daily Health Scores",
            xaxis_title="Date",
            yaxis_title="Score",
            hovermode='x unified',
            height=400,
            showlegend=True,
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Activity and Recovery Balance
        col1, col2 = st.columns(2)
        
        with col1:
            if 'steps' in df_summary.columns:
                # Steps chart
                fig_steps = px.bar(
                    df_summary,
                    x='date',
                    y='steps',
                    title='Daily Steps',
                    color='steps',
                    color_continuous_scale='Blues'
                )
                fig_steps.add_hline(y=10000, line_dash="dash", 
                                  annotation_text="10k Goal")
                fig_steps.update_layout(height=350)
                st.plotly_chart(fig_steps, use_container_width=True)
        
        with col2:
            if 'hrv_balance' in df_summary.columns:
                # HRV Balance chart
                fig_hrv = px.line(
                    df_summary,
                    x='date',
                    y='hrv_balance',
                    title='HRV Balance Trend',
                    markers=True
                )
                fig_hrv.update_traces(line_color='#96CEB4', line_width=3)
                fig_hrv.update_layout(height=350)
                st.plotly_chart(fig_hrv, use_container_width=True)

elif page == "Sleep Analysis":
    st.title("🌙 Sleep Analysis")
    
    # Get sleep data
    df_sleep = st.session_state.queries.get_sleep_periods_df(start_date, end_date)
    
    if not df_sleep.empty:
        # Sleep metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_sleep = df_sleep[df_sleep['type'] == 'long_sleep']['total_sleep_hours'].mean()
            st.metric("Avg Sleep Duration", f"{avg_sleep:.1f}h")
        
        with col2:
            avg_efficiency = df_sleep[df_sleep['type'] == 'long_sleep']['efficiency_percent'].mean()
            st.metric("Avg Sleep Efficiency", f"{avg_efficiency:.0f}%")
        
        with col3:
            avg_hrv = df_sleep['hrv_avg'].mean()
            if pd.notna(avg_hrv):
                st.metric("Avg HRV", f"{avg_hrv:.0f}")
        
        with col4:
            avg_hr = df_sleep['heart_rate_avg'].mean()
            if pd.notna(avg_hr):
                st.metric("Avg Heart Rate", f"{avg_hr:.0f} bpm")
        
        st.markdown("---")
        
        # Sleep stages breakdown
        st.subheader("Sleep Stages Analysis")
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Sleep Duration Trend', 'Sleep Stages Distribution',
                          'Sleep Efficiency', 'Heart Rate & HRV'),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # Filter for main sleep only
        df_main_sleep = df_sleep[df_sleep['type'] == 'long_sleep'].copy()
        
        # 1. Sleep duration trend
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['total_sleep_hours'],
                mode='lines+markers',
                name='Sleep Hours',
                line=dict(color='#4ECDC4', width=3)
            ),
            row=1, col=1
        )
        
        # 2. Sleep stages distribution (stacked area)
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['deep_hours'],
                mode='lines',
                name='Deep Sleep',
                stackgroup='one',
                fillcolor='#1f77b4'
            ),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['rem_hours'],
                mode='lines',
                name='REM Sleep',
                stackgroup='one',
                fillcolor='#ff7f0e'
            ),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['light_hours'],
                mode='lines',
                name='Light Sleep',
                stackgroup='one',
                fillcolor='#2ca02c'
            ),
            row=1, col=2
        )
        
        # 3. Sleep efficiency
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['efficiency_percent'],
                mode='lines+markers',
                name='Efficiency %',
                line=dict(color='#96CEB4', width=3)
            ),
            row=2, col=1
        )
        fig.add_hline(y=85, line_dash="dash", line_color="gray", 
                     row=2, col=1)
        
        # 4. Heart rate and HRV
        if 'heart_rate_avg' in df_main_sleep.columns and 'hrv_avg' in df_main_sleep.columns:
            # Create secondary y-axis
            fig.add_trace(
                go.Scatter(
                    x=df_main_sleep['date'],
                    y=df_main_sleep['heart_rate_avg'],
                    mode='lines+markers',
                    name='Heart Rate',
                    line=dict(color='#ff6b6b', width=2)
                ),
                row=2, col=2
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df_main_sleep['date'],
                    y=df_main_sleep['hrv_avg'],
                    mode='lines+markers',
                    name='HRV',
                    line=dict(color='#45b7d1', width=2),
                    yaxis='y2'
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=2)
        fig.update_yaxes(title_text="Hours", row=1, col=1)
        fig.update_yaxes(title_text="Hours", row=1, col=2)
        fig.update_yaxes(title_text="Percentage", row=2, col=1)
        fig.update_yaxes(title_text="BPM", row=2, col=2)
        
        fig.update_layout(height=800, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Sleep quality insights
        st.subheader("Sleep Quality Insights")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Average sleep stages
            avg_stages = df_main_sleep[['rem_percentage', 'deep_percentage', 'light_percentage']].mean()
            fig_pie = px.pie(
                values=avg_stages.values,
                names=['REM', 'Deep', 'Light'],
                title='Average Sleep Stage Distribution',
                color_discrete_map={'REM': '#ff7f0e', 'Deep': '#1f77b4', 'Light': '#2ca02c'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Sleep consistency
            sleep_std = df_main_sleep['total_sleep_hours'].std()
            st.markdown("### Sleep Consistency")
            if sleep_std < 1:
                st.success(f"Excellent! Std Dev: {sleep_std:.2f}h")
            elif sleep_std < 1.5:
                st.warning(f"Good. Std Dev: {sleep_std:.2f}h")
            else:
                st.error(f"Needs improvement. Std Dev: {sleep_std:.2f}h")
            
            # Latency analysis
            avg_latency = df_main_sleep['latency_minutes'].mean()
            st.markdown("### Sleep Latency")
            if avg_latency < 15:
                st.success(f"Excellent! Avg: {avg_latency:.0f} min")
            elif avg_latency < 30:
                st.warning(f"Good. Avg: {avg_latency:.0f} min")
            else:
                st.error(f"Poor. Avg: {avg_latency:.0f} min")
        
        with col3:
            # Sleep recommendations
            st.markdown("### Recommendations")
            
            if avg_sleep < 7:
                st.info("💡 Try to get at least 7-9 hours of sleep")
            
            if avg_efficiency < 85:
                st.info("💡 Improve sleep efficiency by maintaining consistent sleep schedule")
            
            if avg_stages['deep_percentage'] < 15:
                st.info("💡 Increase deep sleep with regular exercise and cooler room temperature")

elif page == "Activity Tracking":
    st.title("🏃 Activity Tracking")
    
    # Get activity data
    df_activity = st.session_state.queries.get_activity_df(start_date, end_date)
    df_workouts = st.session_state.queries.get_workouts_df(start_date, end_date)
    
    if not df_activity.empty:
        # Activity metrics
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
        
        st.markdown("---")
        
        # Activity visualizations
        tab1, tab2, tab3 = st.tabs(["Daily Activity", "Activity Patterns", "Workouts"])
        
        with tab1:
            # Steps and activity score
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Daily Steps vs Goal', 'Activity Score Trend'),
                vertical_spacing=0.15
            )
            
            # Steps bar chart
            fig.add_trace(
                go.Bar(
                    x=df_activity['date'],
                    y=df_activity['steps'],
                    name='Steps',
                    marker_color=df_activity['steps'].apply(
                        lambda x: '#45B7D1' if x >= 10000 else '#FFB6C1'
                    )
                ),
                row=1, col=1
            )
            fig.add_hline(y=10000, line_dash="dash", line_color="gray", row=1, col=1)
            
            # Activity score line
            fig.add_trace(
                go.Scatter(
                    x=df_activity['date'],
                    y=df_activity['activity_score'],
                    mode='lines+markers',
                    name='Activity Score',
                    line=dict(color='#45B7D1', width=3)
                ),
                row=2, col=1
            )
            
            fig.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Activity patterns
            col1, col2 = st.columns(2)
            
            with col1:
                # Activity time distribution
                activity_dist = df_activity[['high_activity_minutes', 
                                           'medium_activity_minutes', 
                                           'low_activity_minutes']].mean()
                fig_dist = px.pie(
                    values=activity_dist.values,
                    names=['High', 'Medium', 'Low'],
                    title='Average Activity Intensity Distribution',
                    color_discrete_map={'High': '#ff6b6b', 'Medium': '#ffd93d', 'Low': '#6bcf7f'}
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                # Day of week patterns
                df_activity['day_of_week'] = df_activity['date'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                dow_steps = df_activity.groupby('day_of_week')['steps'].mean().reindex(day_order)
                fig_dow = px.bar(
                    x=dow_steps.index,
                    y=dow_steps.values,
                    title='Average Steps by Day of Week',
                    labels={'x': 'Day', 'y': 'Steps'}
                )
                st.plotly_chart(fig_dow, use_container_width=True)
            
            # Sedentary time analysis
            st.subheader("Sedentary Time Analysis")
            sedentary_pct = (df_activity['sedentary_minutes'] / (24 * 60) * 100).mean()
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = 100 - sedentary_pct,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Active Time %"},
                    delta = {'reference': 50},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 25], 'color': "lightgray"},
                            {'range': [25, 50], 'color': "gray"},
                            {'range': [50, 75], 'color': "lightgreen"},
                            {'range': [75, 100], 'color': "green"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)
        
        with tab3:
            # Workouts analysis
            if not df_workouts.empty:
                st.subheader("Workout Summary")
                
                # Workout metrics
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
                
                # Workout types
                workout_types = df_workouts['activity'].value_counts()
                fig_types = px.bar(
                    x=workout_types.index,
                    y=workout_types.values,
                    title='Workouts by Type',
                    labels={'x': 'Activity Type', 'y': 'Count'}
                )
                st.plotly_chart(fig_types, use_container_width=True)
                
                # Workout timeline
                fig_timeline = px.scatter(
                    df_workouts,
                    x='date',
                    y='duration_minutes',
                    size='calories',
                    color='activity',
                    title='Workout Timeline',
                    hover_data=['intensity', 'distance_km']
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("No workout data available for this period")

elif page == "Readiness & Recovery":
    st.title("💪 Readiness & Recovery")
    
    # Get readiness and stress data
    df_readiness = st.session_state.queries.get_readiness_df(start_date, end_date)
    df_stress = st.session_state.queries.get_stress_df(start_date, end_date)
    
    if not df_readiness.empty:
        # Readiness metrics
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
            if not df_stress.empty:
                avg_stress_ratio = df_stress['stress_recovery_ratio'].mean()
                if pd.notna(avg_stress_ratio):
                    st.metric("Avg Stress Ratio", f"{avg_stress_ratio:.2f}")
        
        st.markdown("---")
        
        # Readiness visualizations
        tab1, tab2, tab3 = st.tabs(["Readiness Trends", "Recovery Factors", "Stress Analysis"])
        
        with tab1:
            # Readiness score trend
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_readiness['date'],
                y=df_readiness['readiness_score'],
                mode='lines+markers',
                name='Readiness Score',
                line=dict(color='#45B7D1', width=3),
                fill='tozeroy',
                fillcolor='rgba(69, 183, 209, 0.2)'
            ))
            
            # Add optimal zone
            fig.add_hrect(y0=85, y1=100, 
                         fillcolor="green", opacity=0.1,
                         annotation_text="Optimal", annotation_position="top left")
            fig.add_hrect(y0=70, y1=85, 
                         fillcolor="yellow", opacity=0.1,
                         annotation_text="Good", annotation_position="top left")
            fig.add_hrect(y0=0, y1=70, 
                         fillcolor="red", opacity=0.1,
                         annotation_text="Rest", annotation_position="top left")
            
            fig.update_layout(
                title="Daily Readiness Score",
                xaxis_title="Date",
                yaxis_title="Score",
                height=400,
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Contributors breakdown
            st.subheader("Readiness Contributors")
            
            contributors = [col for col in df_readiness.columns if col.startswith('score_')]
            if contributors:
                # Calculate average contributor scores
                contrib_data = df_readiness[contributors].mean()
                contrib_data.index = contrib_data.index.str.replace('score_', '').str.replace('_', ' ').str.title()
                
                fig_contrib = px.bar(
                    x=contrib_data.values,
                    y=contrib_data.index,
                    orientation='h',
                    title='Average Contributor Scores',
                    labels={'x': 'Score', 'y': 'Contributor'}
                )
                fig_contrib.update_traces(marker_color='#45B7D1')
                st.plotly_chart(fig_contrib, use_container_width=True)
        
        with tab2:
            # Recovery factors
            col1, col2 = st.columns(2)
            
            with col1:
                # HRV Balance trend
                if 'hrv_balance' in df_readiness.columns:
                    fig_hrv = px.line(
                        df_readiness,
                        x='date',
                        y='hrv_balance',
                        title='HRV Balance Trend',
                        markers=True
                    )
                    fig_hrv.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_hrv.update_traces(line_color='#96CEB4', line_width=3)
                    st.plotly_chart(fig_hrv, use_container_width=True)
            
            with col2:
                # Resting heart rate trend
                if 'resting_heart_rate' in df_readiness.columns:
                    fig_rhr = px.line(
                        df_readiness,
                        x='date',
                        y='resting_heart_rate',
                        title='Resting Heart Rate Trend',
                        markers=True
                    )
                    fig_rhr.update_traces(line_color='#ff6b6b', line_width=3)
                    st.plotly_chart(fig_rhr, use_container_width=True)
            
            # Temperature deviation
            if 'temperature_deviation' in df_readiness.columns:
                st.subheader("Body Temperature Deviation")
                fig_temp = go.Figure()
                
                # Add bars for temperature deviation
                colors = ['red' if x > 0 else 'blue' for x in df_readiness['temperature_deviation']]
                fig_temp.add_trace(go.Bar(
                    x=df_readiness['date'],
                    y=df_readiness['temperature_deviation'],
                    marker_color=colors,
                    name='Temperature Deviation'
                ))
                
                fig_temp.add_hline(y=0, line_dash="solid", line_color="gray")
                fig_temp.update_layout(
                    title="Daily Temperature Deviation from Baseline",
                    xaxis_title="Date",
                    yaxis_title="Deviation (°C)",
                    height=350
                )
                st.plotly_chart(fig_temp, use_container_width=True)
        
        with tab3:
            # Stress analysis
            if not df_stress.empty:
                st.subheader("Stress & Recovery Balance")
                
                # Stress vs Recovery minutes
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Daily Stress vs Recovery Minutes', 'Stress/Recovery Ratio'),
                    vertical_spacing=0.15
                )
                
                # Stacked bar chart
                fig.add_trace(
                    go.Bar(
                        x=df_stress['date'],
                        y=df_stress['stress_high_minutes'],
                        name='Stress Minutes',
                        marker_color='#ff6b6b'
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Bar(
                        x=df_stress['date'],
                        y=df_stress['recovery_high_minutes'],
                        name='Recovery Minutes',
                        marker_color='#6bcf7f'
                    ),
                    row=1, col=1
                )
                
                # Ratio line chart
                fig.add_trace(
                    go.Scatter(
                        x=df_stress['date'],
                        y=df_stress['stress_recovery_ratio'],
                        mode='lines+markers',
                        name='Stress/Recovery Ratio',
                        line=dict(color='#FFD93D', width=3)
                    ),
                    row=2, col=1
                )
                
                fig.add_hline(y=1, line_dash="dash", line_color="gray", 
                            annotation_text="Balanced", row=2, col=1)
                
                fig.update_layout(height=600, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
                
                # Stress insights
                avg_stress_min = df_stress['stress_high_minutes'].mean()
                avg_recovery_min = df_stress['recovery_high_minutes'].mean()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### Daily Averages")
                    st.info(f"Stress: {avg_stress_min:.0f} min")
                    st.success(f"Recovery: {avg_recovery_min:.0f} min")
                
                with col2:
                    st.markdown("### Balance Status")
                    if avg_stress_min > avg_recovery_min * 1.5:
                        st.error("High stress - needs more recovery")
                    elif avg_stress_min > avg_recovery_min:
                        st.warning("Moderate stress - monitor closely")
                    else:
                        st.success("Good balance!")
                
                with col3:
                    st.markdown("### Recommendations")
                    if avg_stress_min > avg_recovery_min:
                        st.info("💡 Try meditation or breathing exercises")
                        st.info("💡 Take regular breaks during work")
            else:
                st.info("No stress data available for this period")

elif page == "Trends & Insights":
    st.title("📈 Trends & Insights")
    
    # Get trends data
    sleep_trends = st.session_state.queries.get_sleep_trends(30)
    activity_trends = st.session_state.queries.get_activity_trends(30)
    correlations = st.session_state.queries.get_health_correlations(30)
    weekly_summary = st.session_state.queries.get_weekly_summary(4)
    
    # Trend summary
    st.subheader("30-Day Trend Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Sleep Trends")
        if sleep_trends:
            trend_icon = "📈" if sleep_trends.get('trend_sleep_hours') == 'increasing' else "📉"
            st.metric(
                "Avg Sleep Duration",
                f"{sleep_trends.get('avg_sleep_hours', 0):.1f}h",
                f"{trend_icon} {sleep_trends.get('trend_sleep_hours', 'unknown')}"
            )
            st.metric(
                "Avg Sleep Efficiency",
                f"{sleep_trends.get('avg_efficiency', 0):.0f}%"
            )
    
    with col2:
        st.markdown("### Activity Trends")
        if activity_trends:
            trend_icon = "📈" if activity_trends.get('trend_steps') == 'increasing' else "📉"
            st.metric(
                "Avg Daily Steps",
                f"{activity_trends.get('avg_steps', 0):,.0f}",
                f"{trend_icon} {activity_trends.get('trend_steps', 'unknown')}"
            )
            st.metric(
                "Days Above 10k Steps",
                f"{activity_trends.get('days_above_10k_steps', 0)}"
            )
    
    with col3:
        st.markdown("### Recovery Trends")
        if sleep_trends:
            hrv_trend_icon = "📈" if sleep_trends.get('trend_hrv') == 'increasing' else "📉"
            st.metric(
                "Avg HRV",
                f"{sleep_trends.get('avg_hrv', 0):.0f}",
                f"{hrv_trend_icon} {sleep_trends.get('trend_hrv', 'unknown')}"
            )
    
    st.markdown("---")
    
    # Correlations
    st.subheader("Health Metric Correlations")
    
    if not correlations.empty:
        # Create correlation heatmap
        fig_corr = px.imshow(
            correlations,
            labels=dict(color="Correlation"),
            x=correlations.columns,
            y=correlations.columns,
            color_continuous_scale='RdBu',
            zmin=-1, zmax=1,
            title="Correlation Matrix of Health Metrics"
        )
        fig_corr.update_layout(height=600)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Key insights
        st.subheader("Key Insights")
        
        # Find strongest correlations
        corr_values = correlations.values
        np.fill_diagonal(corr_values, 0)  # Remove self-correlations
        
        # Get indices of highest correlations
        high_corr_indices = np.unravel_index(np.argsort(np.abs(corr_values.ravel()))[-3:], corr_values.shape)
        
        for i in range(3):
            row_idx = high_corr_indices[0][-(i+1)]
            col_idx = high_corr_indices[1][-(i+1)]
            metric1 = correlations.index[row_idx]
            metric2 = correlations.columns[col_idx]
            corr_value = correlations.iloc[row_idx, col_idx]
            
            if corr_value > 0:
                st.success(f"Strong positive correlation ({corr_value:.2f}) between {metric1} and {metric2}")
            else:
                st.warning(f"Strong negative correlation ({corr_value:.2f}) between {metric1} and {metric2}")
    
    # Weekly trends
    if not weekly_summary.empty:
        st.subheader("Weekly Trends")
        
        # Create multi-line chart for weekly averages
        fig_weekly = go.Figure()
        
        metrics = ['sleep_score', 'activity_score', 'readiness_score', 'overall_health_score']
        colors = ['#4ECDC4', '#45B7D1', '#96CEB4', '#FF6B6B']
        
        for metric, color in zip(metrics, colors):
            if metric in weekly_summary.columns:
                fig_weekly.add_trace(go.Scatter(
                    x=weekly_summary['week_start'],
                    y=weekly_summary[metric],
                    mode='lines+markers',
                    name=metric.replace('_', ' ').title(),
                    line=dict(color=color, width=3),
                    marker=dict(size=8)
                ))
        
        fig_weekly.update_layout(
            title="Weekly Average Scores",
            xaxis_title="Week Starting",
            yaxis_title="Score",
            height=400,
            hovermode='x unified',
            yaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

elif page == "Detailed Reports":
    st.title("📊 Detailed Reports")
    
    report_type = st.selectbox(
        "Select Report Type",
        ["Sleep Quality Report", "Activity Performance Report", "Recovery Status Report", "Custom Date Range Report"]
    )
    
    if report_type == "Sleep Quality Report":
        st.subheader("Sleep Quality Analysis Report")
        
        # Get sleep data
        df_sleep = st.session_state.queries.get_sleep_periods_df(start_date, end_date)
        
        if not df_sleep.empty:
            # Sleep statistics
            df_main_sleep = df_sleep[df_sleep['type'] == 'long_sleep']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Sleep Duration Statistics")
                st.write(f"Average: {df_main_sleep['total_sleep_hours'].mean():.1f} hours")
                st.write(f"Minimum: {df_main_sleep['total_sleep_hours'].min():.1f} hours")
                st.write(f"Maximum: {df_main_sleep['total_sleep_hours'].max():.1f} hours")
                st.write(f"Std Dev: {df_main_sleep['total_sleep_hours'].std():.2f} hours")
            
            with col2:
                st.markdown("### Sleep Quality Metrics")
                st.write(f"Avg Efficiency: {df_main_sleep['efficiency_percent'].mean():.1f}%")
                st.write(f"Avg Latency: {df_main_sleep['latency_minutes'].mean():.0f} minutes")
                st.write(f"Avg HRV: {df_main_sleep['hrv_avg'].mean():.0f}")
                st.write(f"Avg Heart Rate: {df_main_sleep['heart_rate_avg'].mean():.0f} bpm")
            
            # Sleep stages breakdown
            st.markdown("### Sleep Stages Analysis")
            
            stages_data = {
                'Stage': ['REM', 'Deep', 'Light'],
                'Average %': [
                    df_main_sleep['rem_percentage'].mean(),
                    df_main_sleep['deep_percentage'].mean(),
                    df_main_sleep['light_percentage'].mean()
                ],
                'Recommended %': [20, 20, 60]
            }
            
            stages_df = pd.DataFrame(stages_data)
            
            fig_stages = go.Figure()
            fig_stages.add_trace(go.Bar(
                x=stages_df['Stage'],
                y=stages_df['Average %'],
                name='Your Average',
                marker_color='lightblue'
            ))
            fig_stages.add_trace(go.Bar(
                x=stages_df['Stage'],
                y=stages_df['Recommended %'],
                name='Recommended',
                marker_color='lightgreen'
            ))
            
            fig_stages.update_layout(
                title="Sleep Stages: Your Average vs Recommended",
                barmode='group',
                yaxis_title="Percentage"
            )
            st.plotly_chart(fig_stages, use_container_width=True)
            
            # Generate recommendations
            st.markdown("### Personalized Recommendations")
            
            recommendations = []
            
            if df_main_sleep['total_sleep_hours'].mean() < 7:
                recommendations.append("🛏️ **Increase sleep duration**: Aim for 7-9 hours of sleep per night")
            
            if df_main_sleep['efficiency_percent'].mean() < 85:
                recommendations.append("⏰ **Improve sleep efficiency**: Maintain consistent bedtime and wake time")
            
            if df_main_sleep['deep_percentage'].mean() < 15:
                recommendations.append("💪 **Boost deep sleep**: Exercise regularly and keep bedroom cool (60-67°F)")
            
            if df_main_sleep['latency_minutes'].mean() > 20:
                recommendations.append("😴 **Reduce sleep latency**: Develop a relaxing bedtime routine")
            
            if df_main_sleep['hrv_avg'].mean() < 30:
                recommendations.append("🧘 **Improve HRV**: Practice stress management and breathing exercises")
            
            for rec in recommendations:
                st.info(rec)
    
    elif report_type == "Activity Performance Report":
        st.subheader("Activity Performance Analysis Report")
        
        df_activity = st.session_state.queries.get_activity_df(start_date, end_date)
        
        if not df_activity.empty:
            # Activity statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### Step Statistics")
                st.write(f"Average: {df_activity['steps'].mean():,.0f}")
                st.write(f"Total: {df_activity['steps'].sum():,.0f}")
                st.write(f"Best Day: {df_activity['steps'].max():,.0f}")
                goal_days = len(df_activity[df_activity['steps'] >= 10000])
                st.write(f"Days at Goal: {goal_days}/{len(df_activity)}")
            
            with col2:
                st.markdown("### Activity Time")
                st.write(f"Active Minutes: {df_activity['total_active_minutes'].mean():.0f}/day")
                st.write(f"High Intensity: {df_activity['high_activity_minutes'].mean():.0f} min")
                st.write(f"Medium Intensity: {df_activity['medium_activity_minutes'].mean():.0f} min")
                st.write(f"Sedentary %: {(df_activity['sedentary_minutes'].mean()/(24*60)*100):.1f}%")
            
            with col3:
                st.markdown("### Calorie Burn")
                st.write(f"Avg Daily: {df_activity['calories_total'].mean():,.0f}")
                st.write(f"Avg Active: {df_activity['calories_active'].mean():,.0f}")
                st.write(f"Total Burned: {df_activity['calories_total'].sum():,.0f}")
                st.write(f"MET Minutes: {df_activity['met_minutes'].mean():.0f}")
            
            # Activity distribution chart
            st.markdown("### Daily Activity Distribution")
            
            # Calculate percentages
            total_minutes = 24 * 60
            activity_distribution = pd.DataFrame({
                'Activity Level': ['High', 'Medium', 'Low', 'Sedentary', 'Non-wear'],
                'Minutes': [
                    df_activity['high_activity_minutes'].mean(),
                    df_activity['medium_activity_minutes'].mean(),
                    df_activity['low_activity_minutes'].mean(),
                    df_activity['sedentary_minutes'].mean(),
                    df_activity['non_wear_minutes'].mean()
                ]
            })
            
            fig_dist = px.pie(
                activity_distribution,
                values='Minutes',
                names='Activity Level',
                title='Average Daily Activity Distribution'
            )
            st.plotly_chart(fig_dist, use_container_width=True)
    
    elif report_type == "Recovery Status Report":
        st.subheader("Recovery Status Analysis Report")
        
        df_readiness = st.session_state.queries.get_readiness_df(start_date, end_date)
        
        if not df_readiness.empty:
            # Recovery metrics
            st.markdown("### Recovery Overview")
            
            # Create a recovery score based on multiple factors
            recovery_score = (
                df_readiness['readiness_score'] * 0.4 +
                df_readiness['score_recovery_index'] * 0.3 +
                df_readiness['score_hrv_balance'] * 0.3
            ).mean()
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = recovery_score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Overall Recovery Status"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkgreen"},
                        'steps': [
                            {'range': [0, 50], 'color': "red"},
                            {'range': [50, 70], 'color': "yellow"},
                            {'range': [70, 85], 'color': "lightgreen"},
                            {'range': [85, 100], 'color': "green"}
                        ],
                        'threshold': {
                            'line': {'color': "black", 'width': 4},
                            'thickness': 0.75,
                            'value': recovery_score
                        }
                    }
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Recovery factors
            st.markdown("### Recovery Factor Analysis")
            
            factors = {
                'HRV Balance': df_readiness['score_hrv_balance'].mean(),
                'Recovery Index': df_readiness['score_recovery_index'].mean(),
                'Resting HR': df_readiness['score_resting_heart_rate'].mean(),
                'Body Temperature': df_readiness['score_body_temperature'].mean(),
                'Sleep Balance': df_readiness['score_sleep_balance'].mean()
            }
            
            factors_df = pd.DataFrame(list(factors.items()), columns=['Factor', 'Score'])
            
            fig_factors = px.bar(
                factors_df,
                x='Score',
                y='Factor',
                orientation='h',
                title='Recovery Factor Scores',
                color='Score',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_factors, use_container_width=True)
    
    elif report_type == "Custom Date Range Report":
        st.subheader("Custom Date Range Analysis")
        
        # Allow custom date selection
        col1, col2 = st.columns(2)
        with col1:
            custom_start = st.date_input("Custom Start Date", value=start_date)
        with col2:
            custom_end = st.date_input("Custom End Date", value=end_date)
        
        if st.button("Generate Custom Report"):
            # Get all data for custom range
            df_summary = st.session_state.queries.get_daily_summary_df(custom_start, custom_end)
            
            if not df_summary.empty:
                # Summary statistics
                st.markdown("### Period Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Days Analyzed", len(df_summary))
                
                with col2:
                    st.metric("Avg Health Score", f"{df_summary['overall_health_score'].mean():.0f}")
                
                with col3:
                    st.metric("Total Steps", f"{df_summary['steps'].sum():,.0f}")
                
                with col4:
                    best_day = df_summary.loc[df_summary['overall_health_score'].idxmax(), 'date']
                    st.metric("Best Day", best_day.strftime('%Y-%m-%d'))
                
                # Create comprehensive chart
                fig = make_subplots(
                    rows=3, cols=1,
                    subplot_titles=('Health Scores', 'Activity Metrics', 'Recovery Indicators'),
                    vertical_spacing=0.1
                )
                
                # Health scores
                for col, name, color in [('sleep_score', 'Sleep', '#4ECDC4'),
                                        ('activity_score', 'Activity', '#45B7D1'),
                                        ('readiness_score', 'Readiness', '#96CEB4')]:
                    if col in df_summary.columns:
                        fig.add_trace(
                            go.Scatter(
                                x=df_summary['date'],
                                y=df_summary[col],
                                mode='lines',
                                name=name,
                                line=dict(color=color, width=2)
                            ),
                            row=1, col=1
                        )
                
                # Activity metrics
                if 'steps' in df_summary.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df_summary['date'],
                            y=df_summary['steps'],
                            name='Steps',
                            marker_color='lightblue',
                            yaxis='y2'
                        ),
                        row=2, col=1
                    )
                
                # Recovery indicators
                if 'hrv_balance' in df_summary.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df_summary['date'],
                            y=df_summary['hrv_balance'],
                            mode='lines+markers',
                            name='HRV Balance',
                            line=dict(color='green', width=2)
                        ),
                        row=3, col=1
                    )
                
                fig.update_layout(height=900, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        Oura Health Dashboard | Data Updated: {} | Made with ❤️ and Streamlit
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
    unsafe_allow_html=True
)