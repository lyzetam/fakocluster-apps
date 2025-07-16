"""
Overview page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
from components.metrics import render_health_score_metrics
from components.charts import create_health_scores_chart, create_steps_chart, create_hrv_balance_chart
from utils.data_processing import calculate_overall_health_score

def render_overview_page(queries, start_date, end_date, personal_info):
    """Render the overview page"""
    st.title("Health Overview Dashboard")
    st.markdown(f"**Date Range:** {start_date} to {end_date}")
    
    # Get enhanced summary data with new metrics
    df_summary = queries.get_enhanced_daily_summary_df(start_date, end_date)
    
    if df_summary.empty:
        st.warning("No data available for the selected date range.")
        return
    
    # Calculate overall health score if missing
    df_summary = calculate_overall_health_score(df_summary)
    
    # Render key metrics
    render_health_score_metrics(df_summary)
    
    # Add advanced metrics summary if available
    render_advanced_metrics_summary(df_summary)
    
    st.markdown("---")
    
    # Overall health score trend
    st.subheader("Health Score Trends")
    fig_scores = create_health_scores_chart(df_summary)
    st.plotly_chart(fig_scores, use_container_width=True)
    
    # Activity and Recovery Balance
    col1, col2 = st.columns(2)
    
    with col1:
        if 'steps' in df_summary.columns:
            fig_steps = create_steps_chart(df_summary)
            st.plotly_chart(fig_steps, use_container_width=True)
    
    with col2:
        if 'hrv_balance' in df_summary.columns:
            fig_hrv = create_hrv_balance_chart(df_summary)
            st.plotly_chart(fig_hrv, use_container_width=True)
    
    # Quick insights
    render_quick_insights(df_summary)

def render_advanced_metrics_summary(df_summary):
    """Render summary of advanced metrics if available"""
    advanced_metrics = []
    
    # Check for VO2 Max
    if 'vo2_max' in df_summary.columns and df_summary['vo2_max'].notna().any():
        latest_vo2 = df_summary[df_summary['vo2_max'].notna()]['vo2_max'].iloc[-1]
        advanced_metrics.append(("VO2 Max", f"{latest_vo2:.1f} mL/kg/min", "🏃"))
    
    # Check for Cardiovascular Age
    if 'cardiovascular_age' in df_summary.columns and df_summary['cardiovascular_age'].notna().any():
        latest_cardio = df_summary[df_summary['cardiovascular_age'].notna()]['cardiovascular_age'].iloc[-1]
        advanced_metrics.append(("Cardio Age", f"{latest_cardio:.0f} years", "❤️"))
    
    # Check for SpO2
    if 'spo2_percentage_avg' in df_summary.columns and df_summary['spo2_percentage_avg'].notna().any():
        avg_spo2 = df_summary['spo2_percentage_avg'].mean()
        advanced_metrics.append(("Avg SpO2", f"{avg_spo2:.1f}%", "🫁"))
    
    # Check for Resilience
    if 'resilience_level' in df_summary.columns and df_summary['resilience_level'].notna().any():
        latest_resilience = df_summary[df_summary['resilience_level'].notna()]['resilience_level'].iloc[-1]
        advanced_metrics.append(("Resilience", latest_resilience.title() if isinstance(latest_resilience, str) else latest_resilience, "💪"))
    
    if advanced_metrics:
        st.subheader("Advanced Health Metrics")
        cols = st.columns(len(advanced_metrics))
        for i, (metric, value, icon) in enumerate(advanced_metrics):
            with cols[i]:
                st.metric(f"{icon} {metric}", value)

def render_quick_insights(df_summary):
    """Render quick insights section"""
    st.subheader("Quick Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Best day
        if 'overall_health_score' in df_summary.columns:
            best_day_idx = df_summary['overall_health_score'].idxmax()
            best_day = df_summary.loc[best_day_idx]
            st.info(f"**Best Day:** {best_day['date'].strftime('%Y-%m-%d')}\nHealth Score: {best_day['overall_health_score']:.0f}")
    
    with col2:
        # Step goal achievement
        if 'steps' in df_summary.columns:
            days_above_10k = len(df_summary[df_summary['steps'] >= 10000])
            total_days = len(df_summary)
            st.info(f"**Step Goal Achievement:** {days_above_10k}/{total_days} days\n({days_above_10k/total_days*100:.0f}% success rate)")
    
    with col3:
        # Average sleep quality
        if 'sleep_score' in df_summary.columns:
            avg_sleep_score = df_summary['sleep_score'].mean()
            sleep_quality = "Excellent" if avg_sleep_score >= 85 else "Good" if avg_sleep_score >= 70 else "Needs Improvement"
            st.info(f"**Sleep Quality:** {sleep_quality}\nAvg Score: {avg_sleep_score:.0f}")
    
    # Trends summary
    st.markdown("### Recent Trends")
    trends_text = analyze_trends(df_summary)
    st.markdown(trends_text)

def analyze_trends(df_summary):
    """Analyze recent trends in the data"""
    trends = []
    
    # Compare last 7 days to previous 7 days
    if len(df_summary) >= 14:
        recent_7 = df_summary.tail(7)
        previous_7 = df_summary.iloc[-14:-7]
        
        # Health score trend
        if 'overall_health_score' in df_summary.columns:
            recent_health = recent_7['overall_health_score'].mean()
            prev_health = previous_7['overall_health_score'].mean()
            
            if recent_health > prev_health + 2:
                trends.append("📈 **Health scores improving** - up {:.0f} points".format(recent_health - prev_health))
            elif recent_health < prev_health - 2:
                trends.append("📉 **Health scores declining** - down {:.0f} points".format(prev_health - recent_health))
        
        # Steps trend
        if 'steps' in df_summary.columns:
            recent_steps = recent_7['steps'].mean()
            prev_steps = previous_7['steps'].mean()
            
            if recent_steps > prev_steps * 1.1:
                trends.append("👟 **More active** - steps up {:.0f}%".format((recent_steps/prev_steps - 1) * 100))
            elif recent_steps < prev_steps * 0.9:
                trends.append("🪑 **Less active** - steps down {:.0f}%".format((1 - recent_steps/prev_steps) * 100))
    
    if not trends:
        trends.append("📊 Not enough data to determine trends")
    
    return "\n\n".join(trends)
