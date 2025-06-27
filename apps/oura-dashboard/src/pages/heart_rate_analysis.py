"""
Heart Rate Analysis page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.charts import apply_chart_theme
from components.metrics import render_metric_card
from utils.data_processing import calculate_moving_average, identify_patterns
from ui_config import COLORS, METRIC_ICONS

def render_heart_rate_analysis_page(queries, start_date, end_date, personal_info):
    """Render the heart rate analysis page"""
    st.title("💓 Heart Rate Analysis")
    
    # Get heart rate data (assuming we add this query method)
    df_hr = queries.get_heart_rate_df(start_date, end_date)
    
    if df_hr.empty:
        st.warning("No heart rate data available for the selected date range.")
        return
    
    # Display metrics
    render_heart_rate_metrics(df_hr)
    
    st.markdown("---")
    
    # Visualizations
    tab1, tab2, tab3 = st.tabs(["Daily Patterns", "Zone Analysis", "Trends"])
    
    with tab1:
        render_daily_patterns_tab(df_hr)
    
    with tab2:
        render_zone_analysis_tab(df_hr)
    
    with tab3:
        render_hr_trends_tab(df_hr)
    
    # Insights and recommendations
    render_hr_insights(df_hr, personal_info)

def render_heart_rate_metrics(df_hr):
    """Render heart rate metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_resting = df_hr['resting_hr'].mean()
        render_metric_card(
            "Avg Resting HR",
            f"{avg_resting:.0f} bpm",
            icon=METRIC_ICONS.get('heart_rate', '❤️')
        )
    
    with col2:
        min_hr = df_hr['min_hr'].min()
        render_metric_card(
            "Lowest HR",
            f"{min_hr:.0f} bpm",
            icon="💙"
        )
    
    with col3:
        max_hr = df_hr['max_hr'].max()
        render_metric_card(
            "Highest HR",
            f"{max_hr:.0f} bpm",
            icon="❤️‍🔥"
        )
    
    with col4:
        avg_variability = df_hr['hr_variability'].mean()
        render_metric_card(
            "Avg Variability",
            f"{avg_variability:.1f}",
            icon="📊"
        )

def render_daily_patterns_tab(df_hr):
    """Render daily heart rate patterns"""
    st.subheader("Daily Heart Rate Patterns")
    
    # Create heart rate range chart
    fig = go.Figure()
    
    # Add min-max range
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['max_hr'],
        mode='lines',
        name='Max HR',
        line=dict(color='rgba(255,0,0,0)'),
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['min_hr'],
        mode='lines',
        name='Min HR',
        fill='tonexty',
        fillcolor='rgba(255,107,107,0.2)',
        line=dict(color='rgba(255,0,0,0)'),
        showlegend=False
    ))
    
    # Add average line
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['avg_hr'],
        mode='lines+markers',
        name='Average HR',
        line=dict(color=COLORS['error'], width=3)
    ))
    
    # Add resting HR
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['resting_hr'],
        mode='lines+markers',
        name='Resting HR',
        line=dict(color=COLORS['activity'], width=2)
    ))
    
    fig.update_layout(
        title="Heart Rate Range and Averages",
        xaxis_title="Date",
        yaxis_title="Heart Rate (bpm)",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)

def render_zone_analysis_tab(df_hr):
    """Render heart rate zone analysis"""
    st.subheader("Heart Rate Zone Distribution")
    
    # Calculate zone percentages (example)
    zones = {
        'Rest': 30,
        'Light': 40,
        'Moderate': 20,
        'Hard': 8,
        'Maximum': 2
    }
    
    colors = ['#4ECDC4', '#45B7D1', '#FFD93D', '#FF6B6B', '#8B0000']
    
    fig = go.Figure(data=[go.Pie(
        labels=list(zones.keys()),
        values=list(zones.values()),
        hole=.3,
        marker_colors=colors
    )])
    
    fig.update_layout(
        title="Time in Heart Rate Zones",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    # Zone descriptions
    st.markdown("### Zone Definitions")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **🟦 Rest Zone (50-60% max HR)**
        - Normal daily activities
        - Recovery state
        
        **🟩 Light Zone (60-70% max HR)**
        - Easy exercise
        - Fat burning zone
        """)
    
    with col2:
        st.info("""
        **🟡 Moderate Zone (70-80% max HR)**
        - Cardio training
        - Improved fitness
        
        **🟥 Hard/Maximum Zone (80-100% max HR)**
        - High intensity training
        - Performance improvement
        """)

def render_hr_trends_tab(df_hr):
    """Render heart rate trends"""
    st.subheader("Heart Rate Trends")
    
    # Add moving averages
    df_hr = calculate_moving_average(df_hr, 'resting_hr', window=7)
    
    # Resting HR trend
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['resting_hr'],
        mode='lines+markers',
        name='Daily Resting HR',
        line=dict(color=COLORS['activity'], width=1),
        opacity=0.6
    ))
    
    fig.add_trace(go.Scatter(
        x=df_hr['date'],
        y=df_hr['resting_hr_ma7'],
        mode='lines',
        name='7-day Average',
        line=dict(color=COLORS['error'], width=3)
    ))
    
    fig.update_layout(
        title="Resting Heart Rate Trend",
        xaxis_title="Date",
        yaxis_title="Heart Rate (bpm)",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    # Trend analysis
    pattern = identify_patterns(df_hr, 'resting_hr')
    
    if pattern == "improving":
        st.success("📉 Resting heart rate is decreasing - good cardiovascular fitness improvement!")
    elif pattern == "declining":
        st.warning("📈 Resting heart rate is increasing - may indicate stress or overtraining")
    else:
        st.info("➡️ Resting heart rate is stable")

def render_hr_insights(df_hr, personal_info):
    """Render heart rate insights and recommendations"""
    st.subheader("💡 Heart Rate Insights")
    
    # Calculate age-based max HR
    if personal_info and personal_info.get('age'):
        age = personal_info['age']
        estimated_max_hr = 220 - age
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Estimated Max HR", f"{estimated_max_hr} bpm")
        
        with col2:
            target_zone_low = int(estimated_max_hr * 0.5)
            target_zone_high = int(estimated_max_hr * 0.85)
            st.metric("Target Zone", f"{target_zone_low}-{target_zone_high} bpm")
        
        with col3:
            avg_resting = df_hr['resting_hr'].mean()
            fitness_score = estimate_fitness_level(avg_resting, age)
            st.metric("Fitness Level", fitness_score)
    
    # Recommendations
    st.markdown("### Recommendations")
    
    avg_resting = df_hr['resting_hr'].mean()
    
    if avg_resting < 60:
        st.success("🏃 Excellent resting heart rate! You have good cardiovascular fitness.")
    elif avg_resting < 70:
        st.info("👍 Good resting heart rate. Regular cardio exercise can improve it further.")
    else:
        st.warning("⚠️ Higher than optimal resting heart rate. Consider:")
        st.markdown("""
        - Increasing aerobic exercise
        - Managing stress levels
        - Improving sleep quality
        - Consulting with a healthcare provider
        """)

def estimate_fitness_level(resting_hr, age):
    """Estimate fitness level based on resting HR and age"""
    # Simplified fitness estimation
    if resting_hr < 55:
        return "Excellent"
    elif resting_hr < 65:
        return "Good"
    elif resting_hr < 75:
        return "Average"
    else:
        return "Below Average"
