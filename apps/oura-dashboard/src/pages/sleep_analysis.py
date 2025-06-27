"""
Sleep Analysis page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
from components.metrics import render_sleep_metrics
from components.charts import create_sleep_analysis_charts, create_sleep_stages_pie
from utils.recommendations import RecommendationEngine
from utils.data_processing import calculate_sleep_consistency

def render_sleep_analysis_page(queries, start_date, end_date, personal_info):
    """Render the sleep analysis page"""
    st.title("🌙 Sleep Analysis")
    
    # Get sleep data
    df_sleep = queries.get_sleep_periods_df(start_date, end_date)
    
    if df_sleep.empty:
        st.warning("No sleep data available for the selected date range.")
        return
    
    # Sleep metrics
    render_sleep_metrics(df_sleep)
    
    st.markdown("---")
    
    # Sleep stages breakdown
    st.subheader("Sleep Stages Analysis")
    
    # Filter for main sleep only
    df_main_sleep = df_sleep[df_sleep['type'] == 'long_sleep'].copy()
    
    # Create comprehensive sleep charts
    fig_sleep = create_sleep_analysis_charts(df_main_sleep)
    st.plotly_chart(fig_sleep, use_container_width=True)
    
    # Sleep quality insights
    render_sleep_quality_insights(df_main_sleep)
    
    # Sleep recommendations
    render_sleep_recommendations(df_sleep)

def render_sleep_quality_insights(df_main_sleep):
    """Render sleep quality insights section"""
    st.subheader("Sleep Quality Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Average sleep stages
        avg_stages = df_main_sleep[['rem_percentage', 'deep_percentage', 'light_percentage']].mean()
        fig_pie = create_sleep_stages_pie(df_main_sleep)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Sleep consistency
        st.markdown("### Sleep Consistency")
        consistency_metrics = calculate_sleep_consistency(df_main_sleep)
        sleep_std = consistency_metrics['sleep_duration_std']
        
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
        # Sleep quality score
        st.markdown("### Sleep Quality Score")
        quality_score = calculate_sleep_quality_score(df_main_sleep)
        render_quality_gauge(quality_score)
    
    # Detailed sleep metrics
    render_detailed_sleep_metrics(df_main_sleep)

def calculate_sleep_quality_score(df_sleep):
    """Calculate overall sleep quality score"""
    # Weighted components
    weights = {
        'efficiency': 0.3,
        'deep_sleep': 0.2,
        'rem_sleep': 0.2,
        'duration': 0.2,
        'latency': 0.1
    }
    
    score = 0
    
    # Efficiency component (target: 85%+)
    avg_efficiency = df_sleep['efficiency_percent'].mean()
    efficiency_score = min(100, (avg_efficiency / 85) * 100)
    score += efficiency_score * weights['efficiency']
    
    # Deep sleep component (target: 15-20%)
    avg_deep = df_sleep['deep_percentage'].mean()
    deep_score = min(100, (avg_deep / 15) * 100) if avg_deep < 20 else max(0, 100 - (avg_deep - 20) * 5)
    score += deep_score * weights['deep_sleep']
    
    # REM sleep component (target: 20-25%)
    avg_rem = df_sleep['rem_percentage'].mean()
    rem_score = min(100, (avg_rem / 20) * 100) if avg_rem < 25 else max(0, 100 - (avg_rem - 25) * 4)
    score += rem_score * weights['rem_sleep']
    
    # Duration component (target: 7-9 hours)
    avg_duration = df_sleep['total_sleep_hours'].mean()
    if 7 <= avg_duration <= 9:
        duration_score = 100
    elif avg_duration < 7:
        duration_score = (avg_duration / 7) * 100
    else:
        duration_score = max(0, 100 - (avg_duration - 9) * 20)
    score += duration_score * weights['duration']
    
    # Latency component (target: <20 min)
    avg_latency = df_sleep['latency_minutes'].mean()
    latency_score = max(0, 100 - (avg_latency / 20) * 50) if avg_latency < 40 else 0
    score += latency_score * weights['latency']
    
    return score

def render_quality_gauge(score):
    """Render a simple quality gauge"""
    if score >= 85:
        st.success(f"🟢 Excellent: {score:.0f}/100")
    elif score >= 70:
        st.warning(f"🟡 Good: {score:.0f}/100")
    else:
        st.error(f"🔴 Needs Improvement: {score:.0f}/100")

def render_detailed_sleep_metrics(df_sleep):
    """Render detailed sleep metrics table"""
    with st.expander("📊 Detailed Sleep Metrics"):
        # Calculate averages and ranges
        metrics = {
            'Total Sleep': f"{df_sleep['total_sleep_hours'].mean():.1f}h ({df_sleep['total_sleep_hours'].min():.1f} - {df_sleep['total_sleep_hours'].max():.1f})",
            'Sleep Efficiency': f"{df_sleep['efficiency_percent'].mean():.0f}% ({df_sleep['efficiency_percent'].min():.0f} - {df_sleep['efficiency_percent'].max():.0f})",
            'REM Sleep': f"{df_sleep['rem_hours'].mean():.1f}h ({df_sleep['rem_percentage'].mean():.0f}%)",
            'Deep Sleep': f"{df_sleep['deep_hours'].mean():.1f}h ({df_sleep['deep_percentage'].mean():.0f}%)",
            'Light Sleep': f"{df_sleep['light_hours'].mean():.1f}h ({df_sleep['light_percentage'].mean():.0f}%)",
            'Awake Time': f"{df_sleep['awake_time'].mean():.0f} min",
            'Sleep Latency': f"{df_sleep['latency_minutes'].mean():.0f} min",
            'Heart Rate': f"{df_sleep['heart_rate_avg'].mean():.0f} bpm" if 'heart_rate_avg' in df_sleep.columns else "N/A",
            'HRV': f"{df_sleep['hrv_avg'].mean():.0f} ms" if 'hrv_avg' in df_sleep.columns else "N/A"
        }
        
        # Display as a nice table
        metrics_df = pd.DataFrame(list(metrics.items()), columns=['Metric', 'Value'])
        st.table(metrics_df)

def render_sleep_recommendations(df_sleep):
    """Render sleep recommendations"""
    st.subheader("💡 Sleep Recommendations")
    
    # Get recommendations
    recommendations = RecommendationEngine.get_sleep_recommendations(df_sleep)
    
    if recommendations:
        # Prioritize and display
        top_recommendations = RecommendationEngine.prioritize_recommendations(recommendations, max_recommendations=5)
        
        for rec in top_recommendations:
            formatted_rec = RecommendationEngine.format_recommendation(rec)
            st.info(formatted_rec)
    else:
        st.success("🎉 Your sleep patterns look great! Keep up the good work.")
    
    # Additional tips
    with st.expander("💤 General Sleep Tips"):
        st.markdown("""
        **Improve Sleep Quality:**
        - 🌙 Keep a consistent sleep schedule
        - 🌡️ Keep bedroom cool (60-67°F)
        - 📱 Avoid screens 1 hour before bed
        - ☕ Limit caffeine after 2 PM
        - 🧘 Practice relaxation techniques
        - 🏃 Exercise regularly (but not too close to bedtime)
        - 🍷 Limit alcohol consumption
        - 🛏️ Invest in a comfortable mattress and pillows
        """)

def render_sleep_trends(df_sleep):
    """Render sleep trends analysis"""
    st.subheader("📈 Sleep Trends")
    
    # Weekly averages
    df_sleep['week'] = pd.to_datetime(df_sleep['date']).dt.to_period('W')
    weekly_avg = df_sleep.groupby('week').agg({
        'total_sleep_hours': 'mean',
        'efficiency_percent': 'mean',
        'sleep_score': 'mean'
    }).reset_index()
    
    # Display trends
    if len(weekly_avg) > 1:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend = "📈" if weekly_avg['total_sleep_hours'].iloc[-1] > weekly_avg['total_sleep_hours'].iloc[0] else "📉"
            st.metric("Sleep Duration Trend", f"{trend} {weekly_avg['total_sleep_hours'].iloc[-1]:.1f}h")
        
        with col2:
            trend = "📈" if weekly_avg['efficiency_percent'].iloc[-1] > weekly_avg['efficiency_percent'].iloc[0] else "📉"
            st.metric("Efficiency Trend", f"{trend} {weekly_avg['efficiency_percent'].iloc[-1]:.0f}%")
        
        with col3:
            if 'sleep_score' in weekly_avg.columns:
                trend = "📈" if weekly_avg['sleep_score'].iloc[-1] > weekly_avg['sleep_score'].iloc[0] else "📉"
                st.metric("Sleep Score Trend", f"{trend} {weekly_avg['sleep_score'].iloc[-1]:.0f}")