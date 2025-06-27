"""
Trends & Insights page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
from components.charts import create_correlation_heatmap, create_weekly_trends_chart
from utils.data_processing import identify_patterns
from ui_config import STATUS_ICONS

def render_trends_insights_page(queries, start_date, end_date, personal_info):
    """Render the trends and insights page"""
    st.title("📈 Trends & Insights")
    
    # Get trends data
    sleep_trends = queries.get_sleep_trends(30)
    activity_trends = queries.get_activity_trends(30)
    correlations = queries.get_health_correlations(30)
    weekly_summary = queries.get_weekly_summary(4)
    
    # Trend summary
    render_trend_summary(sleep_trends, activity_trends)
    
    st.markdown("---")
    
    # Correlations
    if not correlations.empty:
        render_correlations_section(correlations)
    
    # Weekly trends
    if not weekly_summary.empty:
        render_weekly_trends_section(weekly_summary)
    
    # Pattern analysis
    render_pattern_analysis(queries, start_date, end_date)
    
    # Predictive insights
    render_predictive_insights(queries, start_date, end_date)

def render_trend_summary(sleep_trends, activity_trends):
    """Render 30-day trend summary"""
    st.subheader("30-Day Trend Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Sleep Trends")
        if sleep_trends:
            # Sleep duration trend
            sleep_hours = sleep_trends.get('avg_sleep_hours', 0)
            sleep_trend = determine_trend(sleep_trends.get('trend_sleep_hours', 'unknown'))
            st.metric(
                "Avg Sleep Duration",
                f"{sleep_hours:.1f}h",
                f"{sleep_trend['icon']} {sleep_trend['text']}"
            )
            
            # Sleep efficiency
            efficiency = sleep_trends.get('avg_efficiency', 0)
            st.metric(
                "Avg Sleep Efficiency",
                f"{efficiency:.0f}%"
            )
    
    with col2:
        st.markdown("### Activity Trends")
        if activity_trends:
            # Steps trend
            avg_steps = activity_trends.get('avg_steps', 0)
            steps_trend = determine_trend(activity_trends.get('trend_steps', 'unknown'))
            st.metric(
                "Avg Daily Steps",
                f"{avg_steps:,.0f}",
                f"{steps_trend['icon']} {steps_trend['text']}"
            )
            
            # Days above 10k
            days_10k = activity_trends.get('days_above_10k_steps', 0)
            st.metric(
                "Days Above 10k Steps",
                f"{days_10k}"
            )
    
    with col3:
        st.markdown("### Recovery Trends")
        if sleep_trends:
            # HRV trend
            avg_hrv = sleep_trends.get('avg_hrv', 0)
            hrv_trend = determine_trend(sleep_trends.get('trend_hrv', 'unknown'))
            st.metric(
                "Avg HRV",
                f"{avg_hrv:.0f}",
                f"{hrv_trend['icon']} {hrv_trend['text']}"
            )

def determine_trend(trend_value):
    """Determine trend icon and text"""
    if trend_value == 'increasing':
        return {'icon': '📈', 'text': 'Improving'}
    elif trend_value == 'decreasing':
        return {'icon': '📉', 'text': 'Declining'}
    else:
        return {'icon': '➡️', 'text': 'Stable'}

def render_correlations_section(correlations):
    """Render correlations analysis"""
    st.subheader("Health Metric Correlations")
    
    # Create correlation heatmap
    fig_corr = create_correlation_heatmap(correlations)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Key insights
    st.subheader("Key Insights")
    
    # Find strongest correlations
    insights = find_key_correlations(correlations)
    
    for insight in insights:
        if insight['strength'] == 'strong':
            if insight['direction'] == 'positive':
                st.success(insight['text'])
            else:
                st.warning(insight['text'])
        else:
            st.info(insight['text'])

def find_key_correlations(correlations):
    """Find and format key correlation insights"""
    insights = []
    
    # Remove self-correlations
    corr_values = correlations.values
    np.fill_diagonal(corr_values, 0)
    
    # Get indices of highest correlations
    high_corr_indices = np.unravel_index(
        np.argsort(np.abs(corr_values.ravel()))[-5:], 
        corr_values.shape
    )
    
    for i in range(5):
        row_idx = high_corr_indices[0][-(i+1)]
        col_idx = high_corr_indices[1][-(i+1)]
        
        if row_idx != col_idx:  # Skip self-correlations
            metric1 = correlations.index[row_idx]
            metric2 = correlations.columns[col_idx]
            corr_value = correlations.iloc[row_idx, col_idx]
            
            strength = 'strong' if abs(corr_value) > 0.7 else 'moderate'
            direction = 'positive' if corr_value > 0 else 'negative'
            
            insights.append({
                'strength': strength,
                'direction': direction,
                'text': f"{direction.title()} correlation ({corr_value:.2f}) between {format_metric_name(metric1)} and {format_metric_name(metric2)}"
            })
    
    return insights[:3]  # Return top 3 insights

def format_metric_name(metric):
    """Format metric name for display"""
    return metric.replace('_', ' ').title()

def render_weekly_trends_section(weekly_summary):
    """Render weekly trends analysis"""
    st.subheader("Weekly Trends")
    
    # Create multi-line chart
    fig_weekly = create_weekly_trends_chart(weekly_summary)
    st.plotly_chart(fig_weekly, use_container_width=True)
    
    # Weekly insights
    render_weekly_insights(weekly_summary)

def render_weekly_insights(weekly_summary):
    """Render insights from weekly data"""
    st.subheader("Weekly Progress")
    
    # Compare most recent week to first week
    if len(weekly_summary) >= 2:
        first_week = weekly_summary.iloc[0]
        last_week = weekly_summary.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        
        metrics = [
            ('sleep_score', 'Sleep', col1),
            ('activity_score', 'Activity', col2),
            ('readiness_score', 'Readiness', col3),
            ('overall_health_score', 'Overall', col4)
        ]
        
        for metric, name, col in metrics:
            if metric in weekly_summary.columns:
                with col:
                    change = last_week[metric] - first_week[metric]
                    change_pct = (change / first_week[metric]) * 100 if first_week[metric] > 0 else 0
                    
                    if change > 0:
                        st.success(f"{name}: +{change:.0f} ({change_pct:+.0f}%)")
                    elif change < 0:
                        st.error(f"{name}: {change:.0f} ({change_pct:.0f}%)")
                    else:
                        st.info(f"{name}: No change")

def render_pattern_analysis(queries, start_date, end_date):
    """Render pattern analysis section"""
    st.subheader("Pattern Analysis")
    
    # Get recent data for pattern analysis
    df_summary = queries.get_daily_summary_df(start_date, end_date)
    
    if not df_summary.empty and len(df_summary) >= 14:
        patterns = analyze_patterns(df_summary)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Health Patterns")
            for pattern in patterns['health_patterns']:
                st.info(pattern)
        
        with col2:
            st.markdown("### Activity Patterns")
            for pattern in patterns['activity_patterns']:
                st.info(pattern)

def analyze_patterns(df_summary):
    """Analyze patterns in the data"""
    patterns = {
        'health_patterns': [],
        'activity_patterns': []
    }
    
    # Day of week patterns
    df_summary['day_of_week'] = pd.to_datetime(df_summary['date']).dt.day_name()
    
    # Best day for health scores
    if 'overall_health_score' in df_summary.columns:
        best_day = df_summary.groupby('day_of_week')['overall_health_score'].mean().idxmax()
        patterns['health_patterns'].append(f"📅 Best health scores on {best_day}s")
    
    # Most active day
    if 'steps' in df_summary.columns:
        most_active_day = df_summary.groupby('day_of_week')['steps'].mean().idxmax()
        patterns['activity_patterns'].append(f"🏃 Most active on {most_active_day}s")
    
    # Weekend vs weekday
    df_summary['is_weekend'] = pd.to_datetime(df_summary['date']).dt.dayofweek >= 5
    
    if 'sleep_score' in df_summary.columns:
        weekend_sleep = df_summary[df_summary['is_weekend']]['sleep_score'].mean()
        weekday_sleep = df_summary[~df_summary['is_weekend']]['sleep_score'].mean()
        
        if weekend_sleep > weekday_sleep + 5:
            patterns['health_patterns'].append("😴 Better sleep on weekends")
        elif weekday_sleep > weekend_sleep + 5:
            patterns['health_patterns'].append("😴 Better sleep on weekdays")
    
    # Consistency patterns
    if 'steps' in df_summary.columns:
        steps_cv = df_summary['steps'].std() / df_summary['steps'].mean()
        if steps_cv < 0.2:
            patterns['activity_patterns'].append("👏 Very consistent step count")
        elif steps_cv > 0.5:
            patterns['activity_patterns'].append("📊 Highly variable step count")
    
    return patterns

def render_predictive_insights(queries, start_date, end_date):
    """Render predictive insights based on trends"""
    st.subheader("Predictive Insights")
    
    # Get recent data
    df_summary = queries.get_daily_summary_df(start_date, end_date)
    
    if not df_summary.empty and len(df_summary) >= 7:
        insights = generate_predictive_insights(df_summary)
        
        for insight in insights:
            if insight['type'] == 'warning':
                st.warning(f"{STATUS_ICONS['warning']} {insight['text']}")
            elif insight['type'] == 'success':
                st.success(f"{STATUS_ICONS['good']} {insight['text']}")
            else:
                st.info(f"{STATUS_ICONS['info']} {insight['text']}")

def generate_predictive_insights(df_summary):
    """Generate predictive insights based on recent trends"""
    insights = []
    
    # Check recent trends
    if len(df_summary) >= 14:
        # Health score trend
        if 'overall_health_score' in df_summary.columns:
            recent_avg = df_summary['overall_health_score'].tail(7).mean()
            previous_avg = df_summary['overall_health_score'].iloc[-14:-7].mean()
            
            if recent_avg < previous_avg - 5:
                insights.append({
                    'type': 'warning',
                    'text': 'Health scores declining - consider adjusting sleep or activity habits'
                })
            elif recent_avg > previous_avg + 5:
                insights.append({
                    'type': 'success',
                    'text': 'Great progress! Health scores are improving'
                })
        
        # Sleep debt accumulation
        if 'sleep_score' in df_summary.columns:
            low_sleep_days = len(df_summary[df_summary['sleep_score'] < 70].tail(7))
            if low_sleep_days >= 3:
                insights.append({
                    'type': 'warning',
                    'text': f'{low_sleep_days} poor sleep days in the past week - prioritize recovery'
                })
        
        # Activity momentum
        if 'steps' in df_summary.columns:
            recent_steps = df_summary['steps'].tail(7).mean()
            if recent_steps < 5000:
                insights.append({
                    'type': 'warning',
                    'text': 'Low activity levels detected - try to increase daily movement'
                })
            elif recent_steps > 12000:
                insights.append({
                    'type': 'success',
                    'text': 'Excellent activity levels! Keep up the momentum'
                })
    
    if not insights:
        insights.append({
            'type': 'info',
            'text': 'Continue monitoring your trends for personalized insights'
        })
    
    return insights