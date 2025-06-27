"""
Activity Tracking page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from components.metrics import render_activity_metrics, render_workout_metrics
from components.charts import create_activity_distribution_chart, apply_chart_theme
from utils.recommendations import RecommendationEngine
from utils.data_processing import add_day_of_week, calculate_activity_trends
from ui_config import COLORS, CHART_COLORS

def render_activity_tracking_page(queries, start_date, end_date, personal_info):
    """Render the activity tracking page"""
    st.title("🏃 Activity Tracking")
    
    # Get activity data
    df_activity = queries.get_activity_df(start_date, end_date)
    df_workouts = queries.get_workouts_df(start_date, end_date)
    
    if df_activity.empty:
        st.warning("No activity data available for the selected date range.")
        return
    
    # Activity metrics
    render_activity_metrics(df_activity)
    
    st.markdown("---")
    
    # Activity visualizations
    tab1, tab2, tab3 = st.tabs(["Daily Activity", "Activity Patterns", "Workouts"])
    
    with tab1:
        render_daily_activity_tab(df_activity)
    
    with tab2:
        render_activity_patterns_tab(df_activity)
    
    with tab3:
        render_workouts_tab(df_workouts)
    
    # Activity recommendations
    render_activity_recommendations(df_activity, df_workouts)

def render_daily_activity_tab(df_activity):
    """Render daily activity visualizations"""
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
                lambda x: COLORS['activity'] if x >= 10000 else '#FFB6C1'
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
            line=dict(color=COLORS['activity'], width=3)
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    # Activity summary
    render_activity_summary(df_activity)

def render_activity_patterns_tab(df_activity):
    """Render activity patterns analysis"""
    col1, col2 = st.columns(2)
    
    with col1:
        # Activity time distribution
        activity_dist = df_activity[['high_activity_minutes', 
                                   'medium_activity_minutes', 
                                   'low_activity_minutes']].mean()
        fig_dist = create_activity_distribution_chart(activity_dist)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        # Day of week patterns
        df_activity = add_day_of_week(df_activity)
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        dow_steps = df_activity.groupby('day_of_week')['steps'].mean().reindex(day_order)
        fig_dow = px.bar(
            x=dow_steps.index,
            y=dow_steps.values,
            title='Average Steps by Day of Week',
            labels={'x': 'Day', 'y': 'Steps'},
            color=dow_steps.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(apply_chart_theme(fig_dow), use_container_width=True)
    
    # Sedentary time analysis
    render_sedentary_analysis(df_activity)
    
    # Activity intensity analysis
    render_activity_intensity_analysis(df_activity)

def render_sedentary_analysis(df_activity):
    """Render sedentary time analysis"""
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
        st.plotly_chart(apply_chart_theme(fig_gauge), use_container_width=True)
    
    # Sedentary insights
    col1, col2 = st.columns(2)
    
    with col1:
        avg_sedentary_hours = df_activity['sedentary_minutes'].mean() / 60
        st.info(f"**Average Sedentary Time:** {avg_sedentary_hours:.1f} hours/day")
    
    with col2:
        if 'inactivity_alerts' in df_activity.columns:
            avg_alerts = df_activity['inactivity_alerts'].mean()
            st.info(f"**Inactivity Alerts:** {avg_alerts:.1f} per day")

def render_activity_intensity_analysis(df_activity):
    """Render activity intensity analysis"""
    st.subheader("Activity Intensity Breakdown")
    
    # Create stacked area chart for activity intensities over time
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_activity['date'],
        y=df_activity['high_activity_minutes'],
        mode='lines',
        name='High Intensity',
        stackgroup='one',
        fillcolor=CHART_COLORS['activity_levels']['high']
    ))
    
    fig.add_trace(go.Scatter(
        x=df_activity['date'],
        y=df_activity['medium_activity_minutes'],
        mode='lines',
        name='Medium Intensity',
        stackgroup='one',
        fillcolor=CHART_COLORS['activity_levels']['medium']
    ))
    
    fig.add_trace(go.Scatter(
        x=df_activity['date'],
        y=df_activity['low_activity_minutes'],
        mode='lines',
        name='Low Intensity',
        stackgroup='one',
        fillcolor=CHART_COLORS['activity_levels']['low']
    ))
    
    fig.update_layout(
        title="Daily Activity Intensity Distribution",
        xaxis_title="Date",
        yaxis_title="Minutes",
        height=400
    )
    
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)

def render_workouts_tab(df_workouts):
    """Render workouts analysis"""
    if df_workouts.empty:
        st.info("No workout data available for this period")
        return
    
    st.subheader("Workout Summary")
    
    # Workout metrics
    render_workout_metrics(df_workouts)
    
    # Workout types
    workout_types = df_workouts['activity'].value_counts()
    fig_types = px.bar(
        x=workout_types.index,
        y=workout_types.values,
        title='Workouts by Type',
        labels={'x': 'Activity Type', 'y': 'Count'},
        color=workout_types.values,
        color_continuous_scale='Viridis'
    )
    st.plotly_chart(apply_chart_theme(fig_types), use_container_width=True)
    
    # Workout timeline
    df_workouts_clean = df_workouts.copy()
    df_workouts_clean['calories'] = df_workouts_clean['calories'].fillna(0)
    
    fig_timeline = px.scatter(
        df_workouts_clean,
        x='date',
        y='duration_minutes',
        size='calories',
        color='activity',
        title='Workout Timeline',
        hover_data=['intensity', 'distance_km']
    )
    fig_timeline.update_traces(marker=dict(sizemin=5))
    st.plotly_chart(apply_chart_theme(fig_timeline), use_container_width=True)
    
    # Workout details table
    with st.expander("📋 Detailed Workout Log"):
        workout_display = df_workouts[['date', 'activity', 'duration_minutes', 'calories', 'distance_km', 'intensity']].copy()
        workout_display['date'] = workout_display['date'].dt.strftime('%Y-%m-%d')
        st.dataframe(workout_display, use_container_width=True)

def render_activity_summary(df_activity):
    """Render activity summary statistics"""
    st.subheader("Activity Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days_goal_met = len(df_activity[df_activity['steps'] >= 10000])
        total_days = len(df_activity)
        st.metric(
            "Days Goal Met",
            f"{days_goal_met}/{total_days}",
            f"{days_goal_met/total_days*100:.0f}%"
        )
    
    with col2:
        avg_met = df_activity['met_minutes'].mean()
        st.metric(
            "Avg MET Minutes",
            f"{avg_met:.0f}",
            "Weekly target: 500+"
        )
    
    with col3:
        total_calories = df_activity['calories_total'].sum()
        st.metric(
            "Total Calories",
            f"{total_calories:,.0f}",
            f"Avg: {df_activity['calories_total'].mean():.0f}/day"
        )
    
    with col4:
        # Calculate activity trends
        trends = calculate_activity_trends(df_activity)
        trend_icon = "📈" if trends['steps_trend'] == 'increasing' else "📉" if trends['steps_trend'] == 'decreasing' else "➡️"
        st.metric(
            "Step Trend",
            f"{trend_icon} {trends['steps_trend'].title()}",
            f"{trends['percent_days_10k']:.0f}% days at goal"
        )

def render_activity_recommendations(df_activity, df_workouts):
    """Render activity recommendations"""
    st.subheader("💡 Activity Recommendations")
    
    # Get activity recommendations
    activity_recs = RecommendationEngine.get_activity_recommendations(df_activity)
    workout_recs = RecommendationEngine.get_workout_recommendations(df_workouts)
    
    all_recommendations = activity_recs + workout_recs
    
    if all_recommendations:
        # Prioritize and display
        top_recommendations = RecommendationEngine.prioritize_recommendations(all_recommendations, max_recommendations=5)
        
        for rec in top_recommendations:
            formatted_rec = RecommendationEngine.format_recommendation(rec)
            if rec['priority'] == 'high':
                st.error(formatted_rec)
            elif rec['priority'] == 'medium':
                st.warning(formatted_rec)
            else:
                st.info(formatted_rec)
    else:
        st.success("🎉 Your activity levels look great! Keep up the excellent work!")
    
    # Activity tips
    with st.expander("🏃 General Activity Tips"):
        st.markdown("""
        **Increase Daily Activity:**
        - 👟 Take the stairs instead of elevators
        - 🚶 Walk during phone calls
        - 🏃 Set hourly movement reminders
        - 🚴 Consider active commuting
        - 🏊 Mix different types of activities
        - 📱 Use a step tracking app
        - 👥 Find an accountability partner
        - 🎯 Set progressive goals
        
        **WHO Recommendations:**
        - 150-300 minutes of moderate activity per week
        - OR 75-150 minutes of vigorous activity per week
        - Muscle strengthening 2+ days per week
        - Reduce sedentary time
        """)