"""
Detailed Reports page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from utils.data_processing import calculate_sleep_quality_score, format_duration
from utils.recommendations import RecommendationEngine
from components.charts import apply_chart_theme, create_readiness_gauge
from ui_config import COLORS, CHART_COLORS

def render_detailed_reports_page(queries, start_date, end_date, personal_info):
    """Render the detailed reports page"""
    st.title("📊 Detailed Reports")
    
    report_type = st.selectbox(
        "Select Report Type",
        ["Sleep Quality Report", "Activity Performance Report", 
         "Recovery Status Report", "Custom Date Range Report"]
    )
    
    if report_type == "Sleep Quality Report":
        render_sleep_quality_report(queries, start_date, end_date)
    elif report_type == "Activity Performance Report":
        render_activity_performance_report(queries, start_date, end_date)
    elif report_type == "Recovery Status Report":
        render_recovery_status_report(queries, start_date, end_date)
    elif report_type == "Custom Date Range Report":
        render_custom_date_report(queries, start_date, end_date)

def render_sleep_quality_report(queries, start_date, end_date):
    """Render comprehensive sleep quality report"""
    st.subheader("Sleep Quality Analysis Report")
    
    # Get sleep data
    df_sleep = queries.get_sleep_periods_df(start_date, end_date)
    
    if df_sleep.empty:
        st.warning("No sleep data available for the selected date range.")
        return
    
    # Filter for main sleep
    df_main_sleep = df_sleep[df_sleep['type'] == 'long_sleep']
    
    # Report header
    st.markdown(f"**Report Period:** {start_date} to {end_date}")
    st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Executive summary
    render_sleep_executive_summary(df_main_sleep)
    
    # Detailed statistics
    render_sleep_detailed_statistics(df_main_sleep)
    
    # Sleep stages analysis
    render_sleep_stages_analysis(df_main_sleep)
    
    # Sleep quality factors
    render_sleep_quality_factors(df_main_sleep)
    
    # Recommendations
    render_sleep_report_recommendations(df_sleep)
    
    # Export button
    if st.button("📥 Export Report"):
        st.info("Export functionality coming soon!")

def render_sleep_executive_summary(df_main_sleep):
    """Render executive summary for sleep report"""
    st.markdown("### Executive Summary")
    
    # Calculate key metrics
    avg_duration = df_main_sleep['total_sleep_hours'].mean()
    avg_efficiency = df_main_sleep['efficiency_percent'].mean()
    quality_score = calculate_sleep_quality_score(df_main_sleep)
    
    # Determine overall assessment
    if quality_score >= 85:
        assessment = "Excellent"
        assessment_color = "green"
    elif quality_score >= 70:
        assessment = "Good"
        assessment_color = "orange"
    else:
        assessment = "Needs Improvement"
        assessment_color = "red"
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Overall Assessment", assessment)
    with col2:
        st.metric("Quality Score", f"{quality_score:.0f}/100")
    with col3:
        st.metric("Avg Duration", f"{avg_duration:.1f}h")
    with col4:
        st.metric("Avg Efficiency", f"{avg_efficiency:.0f}%")
    
    # Summary text
    summary_text = f"""
    During the reporting period, your sleep quality was **{assessment.lower()}** with an average 
    quality score of {quality_score:.0f}/100. You averaged {avg_duration:.1f} hours of sleep per night 
    with {avg_efficiency:.0f}% efficiency. 
    """
    
    if quality_score < 70:
        summary_text += """
        There are significant opportunities for improvement in your sleep patterns. 
        Please review the recommendations section for specific actions.
        """
    elif quality_score < 85:
        summary_text += """
        Your sleep is generally good, but there's room for optimization. 
        Focus on the areas highlighted in the recommendations.
        """
    else:
        summary_text += """
        You're maintaining excellent sleep habits. Continue your current routine 
        while monitoring for any changes.
        """
    
    st.info(summary_text)

def render_sleep_detailed_statistics(df_main_sleep):
    """Render detailed sleep statistics"""
    st.markdown("### Detailed Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Sleep Duration")
        duration_stats = {
            "Average": f"{df_main_sleep['total_sleep_hours'].mean():.1f} hours",
            "Minimum": f"{df_main_sleep['total_sleep_hours'].min():.1f} hours",
            "Maximum": f"{df_main_sleep['total_sleep_hours'].max():.1f} hours",
            "Std Dev": f"{df_main_sleep['total_sleep_hours'].std():.2f} hours",
            "Nights < 7h": len(df_main_sleep[df_main_sleep['total_sleep_hours'] < 7]),
            "Nights > 9h": len(df_main_sleep[df_main_sleep['total_sleep_hours'] > 9])
        }
        for key, value in duration_stats.items():
            st.text(f"{key}: {value}")
    
    with col2:
        st.markdown("#### Sleep Quality Metrics")
        quality_stats = {
            "Avg Efficiency": f"{df_main_sleep['efficiency_percent'].mean():.1f}%",
            "Avg Latency": f"{df_main_sleep['latency_minutes'].mean():.0f} minutes",
            "Avg Awake Time": f"{df_main_sleep['awake_time'].mean():.0f} minutes",
            "Avg HRV": f"{df_main_sleep['hrv_avg'].mean():.0f}" if 'hrv_avg' in df_main_sleep.columns else "N/A",
            "Avg Heart Rate": f"{df_main_sleep['heart_rate_avg'].mean():.0f} bpm" if 'heart_rate_avg' in df_main_sleep.columns else "N/A",
            "Best Night": df_main_sleep.loc[df_main_sleep['efficiency_percent'].idxmax(), 'date'].strftime('%Y-%m-%d')
        }
        for key, value in quality_stats.items():
            st.text(f"{key}: {value}")

def render_sleep_stages_analysis(df_main_sleep):
    """Render sleep stages analysis"""
    st.markdown("### Sleep Stages Analysis")
    
    # Prepare data
    stages_data = {
        'Stage': ['REM', 'Deep', 'Light'],
        'Your Average %': [
            df_main_sleep['rem_percentage'].mean(),
            df_main_sleep['deep_percentage'].mean(),
            df_main_sleep['light_percentage'].mean()
        ],
        'Recommended %': [20, 20, 60],
        'Your Average Hours': [
            df_main_sleep['rem_hours'].mean(),
            df_main_sleep['deep_hours'].mean(),
            df_main_sleep['light_hours'].mean()
        ]
    }
    
    stages_df = pd.DataFrame(stages_data)
    
    # Create comparison chart
    fig_stages = go.Figure()
    
    fig_stages.add_trace(go.Bar(
        x=stages_df['Stage'],
        y=stages_df['Your Average %'],
        name='Your Average',
        marker_color='lightblue',
        text=stages_df['Your Average %'].round(1),
        textposition='auto'
    ))
    
    fig_stages.add_trace(go.Bar(
        x=stages_df['Stage'],
        y=stages_df['Recommended %'],
        name='Recommended',
        marker_color='lightgreen',
        text=stages_df['Recommended %'],
        textposition='auto'
    ))
    
    fig_stages.update_layout(
        title="Sleep Stages: Your Average vs Recommended",
        barmode='group',
        yaxis_title="Percentage of Total Sleep",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig_stages), use_container_width=True)
    
    # Stage insights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rem_status = "✅" if 15 <= stages_df.iloc[0]['Your Average %'] <= 25 else "⚠️"
        st.info(f"{rem_status} **REM Sleep:** {stages_df.iloc[0]['Your Average %']:.1f}% ({stages_df.iloc[0]['Your Average Hours']:.1f}h)")
    
    with col2:
        deep_status = "✅" if 15 <= stages_df.iloc[1]['Your Average %'] <= 25 else "⚠️"
        st.info(f"{deep_status} **Deep Sleep:** {stages_df.iloc[1]['Your Average %']:.1f}% ({stages_df.iloc[1]['Your Average Hours']:.1f}h)")
    
    with col3:
        light_status = "✅" if 50 <= stages_df.iloc[2]['Your Average %'] <= 65 else "⚠️"
        st.info(f"{light_status} **Light Sleep:** {stages_df.iloc[2]['Your Average %']:.1f}% ({stages_df.iloc[2]['Your Average Hours']:.1f}h)")

def render_sleep_quality_factors(df_main_sleep):
    """Render sleep quality factors analysis"""
    st.markdown("### Sleep Quality Factors")
    
    # Time series of key factors
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Sleep Duration', 'Sleep Efficiency', 
                       'Sleep Latency', 'Wake Episodes'),
        vertical_spacing=0.15
    )
    
    # Duration
    fig.add_trace(
        go.Scatter(
            x=df_main_sleep['date'],
            y=df_main_sleep['total_sleep_hours'],
            mode='lines+markers',
            name='Duration',
            line=dict(color=COLORS['sleep'])
        ),
        row=1, col=1
    )
    fig.add_hline(y=7, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_hline(y=9, line_dash="dash", line_color="gray", row=1, col=1)
    
    # Efficiency
    fig.add_trace(
        go.Scatter(
            x=df_main_sleep['date'],
            y=df_main_sleep['efficiency_percent'],
            mode='lines+markers',
            name='Efficiency',
            line=dict(color=COLORS['readiness'])
        ),
        row=1, col=2
    )
    fig.add_hline(y=85, line_dash="dash", line_color="gray", row=1, col=2)
    
    # Latency
    fig.add_trace(
        go.Scatter(
            x=df_main_sleep['date'],
            y=df_main_sleep['latency_minutes'],
            mode='lines+markers',
            name='Latency',
            line=dict(color=COLORS['warning'])
        ),
        row=2, col=1
    )
    fig.add_hline(y=20, line_dash="dash", line_color="gray", row=2, col=1)
    
    # Awake time
    fig.add_trace(
        go.Scatter(
            x=df_main_sleep['date'],
            y=df_main_sleep['awake_time'],
            mode='lines+markers',
            name='Awake Time',
            line=dict(color=COLORS['error'])
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)

def render_sleep_report_recommendations(df_sleep):
    """Render personalized sleep recommendations for report"""
    st.markdown("### Personalized Recommendations")
    
    recommendations = RecommendationEngine.get_sleep_recommendations(df_sleep)
    
    if recommendations:
        # Group by priority
        high_priority = [r for r in recommendations if r['priority'] == 'high']
        medium_priority = [r for r in recommendations if r['priority'] == 'medium']
        low_priority = [r for r in recommendations if r['priority'] == 'low']
        
        if high_priority:
            st.markdown("#### 🔴 High Priority")
            for rec in high_priority:
                st.error(f"{rec['icon']} **{rec['title']}**: {rec['description']}")
        
        if medium_priority:
            st.markdown("#### 🟡 Medium Priority")
            for rec in medium_priority:
                st.warning(f"{rec['icon']} **{rec['title']}**: {rec['description']}")
        
        if low_priority:
            st.markdown("#### 🟢 Low Priority")
            for rec in low_priority:
                st.info(f"{rec['icon']} **{rec['title']}**: {rec['description']}")
    else:
        st.success("🎉 Your sleep patterns are excellent! Continue maintaining your current habits.")

def render_activity_performance_report(queries, start_date, end_date):
    """Render activity performance report"""
    st.subheader("Activity Performance Analysis Report")
    
    df_activity = queries.get_activity_df(start_date, end_date)
    
    if df_activity.empty:
        st.warning("No activity data available for the selected date range.")
        return
    
    # Report header
    st.markdown(f"**Report Period:** {start_date} to {end_date}")
    st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
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
    
    # Calculate activity distribution
    activity_levels = ['High', 'Medium', 'Low', 'Sedentary']
    minutes_data = [
        df_activity['high_activity_minutes'].mean(),
        df_activity['medium_activity_minutes'].mean(),
        df_activity['low_activity_minutes'].mean(),
        df_activity['sedentary_minutes'].mean()
    ]
    
    # Add non-wear if exists
    if 'non_wear_minutes' in df_activity.columns:
        activity_levels.append('Non-wear')
        minutes_data.append(df_activity['non_wear_minutes'].mean())
    
    activity_distribution = pd.DataFrame({
        'Activity Level': activity_levels,
        'Minutes': minutes_data
    })
    
    fig_dist = px.pie(
        activity_distribution,
        values='Minutes',
        names='Activity Level',
        title='Average Daily Activity Distribution',
        color_discrete_map={
            'High': CHART_COLORS['activity_levels']['high'],
            'Medium': CHART_COLORS['activity_levels']['medium'],
            'Low': CHART_COLORS['activity_levels']['low'],
            'Sedentary': CHART_COLORS['activity_levels']['sedentary'],
            'Non-wear': '#cccccc'
        }
    )
    st.plotly_chart(apply_chart_theme(fig_dist), use_container_width=True)
    
    # Performance trends
    render_activity_performance_trends(df_activity)
    
    # Activity recommendations
    st.markdown("### Recommendations")
    recommendations = RecommendationEngine.get_activity_recommendations(df_activity)
    
    for rec in recommendations[:5]:
        formatted_rec = RecommendationEngine.format_recommendation(rec)
        if rec['priority'] == 'high':
            st.error(formatted_rec)
        elif rec['priority'] == 'medium':
            st.warning(formatted_rec)
        else:
            st.info(formatted_rec)

def render_activity_performance_trends(df_activity):
    """Render activity performance trends"""
    st.markdown("### Performance Trends")
    
    # Create trend charts
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Daily Steps', 'Activity Score', 
                       'Active Minutes', 'Calorie Burn')
    )
    
    # Steps
    fig.add_trace(
        go.Scatter(
            x=df_activity['date'],
            y=df_activity['steps'],
            mode='lines+markers',
            name='Steps',
            line=dict(color=COLORS['activity'])
        ),
        row=1, col=1
    )
    
    # Activity score
    fig.add_trace(
        go.Scatter(
            x=df_activity['date'],
            y=df_activity['activity_score'],
            mode='lines+markers',
            name='Score',
            line=dict(color=COLORS['overall'])
        ),
        row=1, col=2
    )
    
    # Active minutes
    fig.add_trace(
        go.Scatter(
            x=df_activity['date'],
            y=df_activity['total_active_minutes'],
            mode='lines+markers',
            name='Active Min',
            line=dict(color=COLORS['success'])
        ),
        row=2, col=1
    )
    
    # Calories
    fig.add_trace(
        go.Scatter(
            x=df_activity['date'],
            y=df_activity['calories_total'],
            mode='lines+markers',
            name='Calories',
            line=dict(color=COLORS['warning'])
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)

def render_recovery_status_report(queries, start_date, end_date):
    """Render recovery status report"""
    st.subheader("Recovery Status Analysis Report")
    
    df_readiness = queries.get_readiness_df(start_date, end_date)
    
    if df_readiness.empty:
        st.warning("No readiness data available for the selected date range.")
        return
    
    # Recovery metrics
    st.markdown("### Recovery Overview")
    
    # Calculate recovery score
    recovery_score = (
        df_readiness['readiness_score'].mean() * 0.4 +
        df_readiness.get('score_recovery_index', df_readiness['readiness_score']).mean() * 0.3 +
        df_readiness.get('score_hrv_balance', df_readiness['readiness_score']).mean() * 0.3
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        fig_gauge = create_readiness_gauge(recovery_score)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Recovery factors
    st.markdown("### Recovery Factor Analysis")
    
    factors = {}
    score_columns = [col for col in df_readiness.columns if col.startswith('score_')]
    
    if score_columns:
        for col in score_columns:
            factor_name = col.replace('score_', '').replace('_', ' ').title()
            factors[factor_name] = df_readiness[col].mean()
    else:
        # Use default factors if score columns don't exist
        factors = {
            'Readiness Score': df_readiness['readiness_score'].mean(),
            'HRV Balance': df_readiness.get('hrv_balance', pd.Series([50])).mean(),
            'Resting HR': 100 - df_readiness.get('resting_heart_rate', pd.Series([60])).mean()
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
    st.plotly_chart(apply_chart_theme(fig_factors), use_container_width=True)
    
    # Recovery insights
    render_recovery_insights(df_readiness)

def render_recovery_insights(df_readiness):
    """Render recovery insights"""
    st.markdown("### Recovery Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # HRV trends
        if 'hrv_balance' in df_readiness.columns:
            avg_hrv_balance = df_readiness['hrv_balance'].mean()
            recent_hrv_balance = df_readiness['hrv_balance'].tail(7).mean()
            
            if recent_hrv_balance > avg_hrv_balance + 5:
                st.success("💚 HRV improving - good recovery")
            elif recent_hrv_balance < avg_hrv_balance - 5:
                st.warning("💛 HRV declining - monitor recovery")
            else:
                st.info("💙 HRV stable")
    
    with col2:
        # Temperature trends
        if 'temperature_deviation' in df_readiness.columns:
            recent_temp = df_readiness['temperature_deviation'].tail(3).mean()
            
            if abs(recent_temp) > 0.5:
                st.warning(f"🌡️ Temperature deviation: {recent_temp:.2f}°C")
            else:
                st.success(f"🌡️ Temperature normal: {recent_temp:.2f}°C")

def render_custom_date_report(queries, start_date, end_date):
    """Render custom date range report"""
    st.subheader("Custom Date Range Analysis")
    
    # Allow custom date selection
    col1, col2 = st.columns(2)
    with col1:
        custom_start = st.date_input("Custom Start Date", value=start_date)
    with col2:
        custom_end = st.date_input("Custom End Date", value=end_date)
    
    if st.button("Generate Custom Report"):
        # Get all data for custom range
        df_summary = queries.get_daily_summary_df(custom_start, custom_end)
        
        if df_summary.empty:
            st.warning("No data available for the selected date range.")
            return
        
        # Summary statistics
        st.markdown("### Period Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Days Analyzed", len(df_summary))
        
        with col2:
            if 'overall_health_score' in df_summary.columns:
                st.metric("Avg Health Score", f"{df_summary['overall_health_score'].mean():.0f}")
        
        with col3:
            if 'steps' in df_summary.columns:
                st.metric("Total Steps", f"{df_summary['steps'].sum():,.0f}")
        
        with col4:
            if 'overall_health_score' in df_summary.columns:
                best_day = df_summary.loc[df_summary['overall_health_score'].idxmax(), 'date']
                st.metric("Best Day", best_day.strftime('%Y-%m-%d'))
        
        # Create comprehensive chart
        render_custom_report_charts(df_summary)

def render_custom_report_charts(df_summary):
    """Render charts for custom report"""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Health Scores', 'Activity Metrics', 'Recovery Indicators'),
        vertical_spacing=0.1
    )
    
    # Health scores
    score_cols = ['sleep_score', 'activity_score', 'readiness_score']
    colors = [COLORS['sleep'], COLORS['activity'], COLORS['readiness']]
    
    for col, color in zip(score_cols, colors):
        if col in df_summary.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_summary['date'],
                    y=df_summary[col],
                    mode='lines',
                    name=col.replace('_', ' ').title(),
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
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)