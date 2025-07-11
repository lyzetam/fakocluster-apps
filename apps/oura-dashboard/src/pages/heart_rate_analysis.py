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
    
    # Info about data sources
    st.info("""
    **Note**: This analysis uses heart rate data from:
    - 🛌 **Sleep periods**: Average, minimum, and maximum heart rate during sleep
    - 💚 **Readiness data**: Daily resting heart rate measurements
    - 📊 **HRV metrics**: Heart rate variability from sleep periods
    
    Continuous daytime heart rate monitoring requires an Oura Ring Gen 3 with the feature enabled.
    """)
    
    # Get heart rate data from sleep and readiness tables
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
        if 'resting_hr' in df_hr.columns and df_hr['resting_hr'].notna().any():
            avg_resting = df_hr['resting_hr'].mean()
            render_metric_card(
                "Avg Resting HR",
                f"{avg_resting:.0f} bpm",
                icon=METRIC_ICONS.get('heart_rate', '❤️')
            )
        else:
            render_metric_card("Avg Resting HR", "N/A", icon="❤️")
    
    with col2:
        if 'min_hr' in df_hr.columns and df_hr['min_hr'].notna().any():
            min_hr = df_hr['min_hr'].min()
            render_metric_card(
                "Lowest HR",
                f"{min_hr:.0f} bpm",
                icon="💙"
            )
        else:
            render_metric_card("Lowest HR", "N/A", icon="💙")
    
    with col3:
        if 'avg_hr' in df_hr.columns and df_hr['avg_hr'].notna().any():
            avg_hr = df_hr['avg_hr'].mean()
            render_metric_card(
                "Avg Sleep HR",
                f"{avg_hr:.0f} bpm",
                icon="😴"
            )
        else:
            render_metric_card("Avg Sleep HR", "N/A", icon="😴")
    
    with col4:
        if 'hrv_avg' in df_hr.columns and df_hr['hrv_avg'].notna().any():
            avg_hrv = df_hr['hrv_avg'].mean()
            render_metric_card(
                "Avg HRV",
                f"{avg_hrv:.0f} ms",
                icon="📊"
            )
        else:
            render_metric_card("Avg HRV", "N/A", icon="📊")

def render_daily_patterns_tab(df_hr):
    """Render daily heart rate patterns"""
    st.subheader("Daily Heart Rate Patterns")
    
    # Create heart rate range chart
    fig = go.Figure()
    
    # Add sleep HR range if available
    if 'min_hr' in df_hr.columns and 'avg_hr' in df_hr.columns:
        # Add min-avg range for sleep HR
        if df_hr['avg_hr'].notna().any():
            fig.add_trace(go.Scatter(
                x=df_hr['date'],
                y=df_hr['avg_hr'],
                mode='lines',
                name='Sleep HR Range',
                line=dict(color='rgba(255,0,0,0)'),
                showlegend=False
            ))
        
        if df_hr['min_hr'].notna().any():
            fig.add_trace(go.Scatter(
                x=df_hr['date'],
                y=df_hr['min_hr'],
                mode='lines',
                name='Min HR',
                fill='tonexty',
                fillcolor='rgba(135,206,235,0.2)',
                line=dict(color='rgba(255,0,0,0)'),
                showlegend=False
            ))
    
    # Add average sleep HR line
    if 'avg_hr' in df_hr.columns and df_hr['avg_hr'].notna().any():
        fig.add_trace(go.Scatter(
            x=df_hr['date'],
            y=df_hr['avg_hr'],
            mode='lines+markers',
            name='Avg Sleep HR',
            line=dict(color=COLORS['sleep'], width=3)
        ))
    
    # Add resting HR
    if 'resting_hr' in df_hr.columns and df_hr['resting_hr'].notna().any():
        fig.add_trace(go.Scatter(
            x=df_hr['date'],
            y=df_hr['resting_hr'],
            mode='lines+markers',
            name='Resting HR',
            line=dict(color=COLORS['readiness'], width=2)
        ))
    
    fig.update_layout(
        title="Heart Rate Patterns (Sleep & Resting)",
        xaxis_title="Date",
        yaxis_title="Heart Rate (bpm)",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)

def render_zone_analysis_tab(df_hr):
    """Render heart rate zone analysis"""
    st.subheader("Sleep Heart Rate Patterns")
    
    # Since we only have sleep data, show sleep-specific analysis
    col1, col2 = st.columns(2)
    
    with col1:
        # HRV analysis
        if 'hrv_avg' in df_hr.columns and df_hr['hrv_avg'].notna().any():
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_hr['date'],
                y=df_hr['hrv_avg'],
                mode='lines+markers',
                name='HRV Average',
                line=dict(color=COLORS['sleep'], width=2)
            ))
            
            if 'hrv_min' in df_hr.columns and 'hrv_max' in df_hr.columns:
                fig.add_trace(go.Scatter(
                    x=df_hr['date'],
                    y=df_hr['hrv_max'],
                    mode='lines',
                    name='HRV Max',
                    line=dict(color='rgba(0,0,0,0)'),
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_hr['date'],
                    y=df_hr['hrv_min'],
                    mode='lines',
                    name='HRV Range',
                    fill='tonexty',
                    fillcolor='rgba(70, 130, 180, 0.2)',
                    line=dict(color='rgba(0,0,0,0)')
                ))
            
            fig.update_layout(
                title="Heart Rate Variability (HRV)",
                xaxis_title="Date",
                yaxis_title="HRV (ms)",
                height=350
            )
            
            st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    with col2:
        # Respiratory rate if available
        if 'respiratory_rate' in df_hr.columns and df_hr['respiratory_rate'].notna().any():
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_hr['date'],
                y=df_hr['respiratory_rate'],
                mode='lines+markers',
                name='Respiratory Rate',
                line=dict(color=COLORS['readiness'], width=2)
            ))
            
            fig.update_layout(
                title="Respiratory Rate During Sleep",
                xaxis_title="Date",
                yaxis_title="Breaths per Minute",
                height=350
            )
            
            st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    # Sleep stage heart rate zones info
    zones = {
        'Deep Sleep': 'Lowest HR, maximum recovery',
        'REM Sleep': 'Variable HR, similar to waking',
        'Light Sleep': 'Moderate HR, transitional',
        'Awake': 'Elevated HR, brief awakenings'
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
    
    # Sleep stage descriptions
    st.markdown("### Sleep Stage Heart Rate Patterns")
    
    for stage, description in zones.items():
        st.markdown(f"**{stage}**: {description}")

def render_hr_trends_tab(df_hr):
    """Render heart rate trends"""
    st.subheader("Heart Rate Trends")
    
    # Check if we have resting HR data
    if 'resting_hr' in df_hr.columns and df_hr['resting_hr'].notna().any():
        # Add moving averages
        df_hr = calculate_moving_average(df_hr, 'resting_hr', window=7)
        
        # Resting HR trend
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_hr['date'],
            y=df_hr['resting_hr'],
            mode='lines+markers',
            name='Daily Resting HR',
            line=dict(color=COLORS['readiness'], width=1),
            opacity=0.6
        ))
        
        if 'resting_hr_ma7' in df_hr.columns:
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
    else:
        st.info("No resting heart rate data available for trend analysis")

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
            if 'resting_hr' in df_hr.columns and df_hr['resting_hr'].notna().any():
                avg_resting = df_hr['resting_hr'].mean()
                fitness_score = estimate_fitness_level(avg_resting, age)
                st.metric("Fitness Level", fitness_score)
            else:
                st.metric("Fitness Level", "N/A")
    
    # Recommendations
    st.markdown("### Recommendations")
    
    if 'resting_hr' in df_hr.columns and df_hr['resting_hr'].notna().any():
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
    else:
        st.info("Resting heart rate data not available. Ensure your Oura ring is syncing readiness data.")
    
    # HRV insights
    if 'hrv_avg' in df_hr.columns and df_hr['hrv_avg'].notna().any():
        avg_hrv = df_hr['hrv_avg'].mean()
        st.markdown("### HRV Insights")
        if avg_hrv > 50:
            st.success(f"💚 Good HRV average ({avg_hrv:.0f} ms) indicates good recovery capacity")
        elif avg_hrv > 30:
            st.info(f"💛 Moderate HRV ({avg_hrv:.0f} ms) - focus on stress management and recovery")
        else:
            st.warning(f"🟠 Low HRV ({avg_hrv:.0f} ms) - prioritize rest and recovery")

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
