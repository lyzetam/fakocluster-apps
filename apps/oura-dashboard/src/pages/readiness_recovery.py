"""
Readiness & Recovery page for Oura Health Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from components.metrics import render_readiness_metrics
from components.charts import create_readiness_gauge, create_stress_recovery_chart, apply_chart_theme
from utils.recommendations import RecommendationEngine
from utils.data_processing import calculate_recovery_score
from ui_config import COLORS

def render_readiness_recovery_page(queries, start_date, end_date, personal_info):
    """Render the readiness and recovery page"""
    st.title("💪 Readiness & Recovery")
    
    # Get readiness and stress data
    df_readiness = queries.get_readiness_df(start_date, end_date)
    df_stress = queries.get_stress_df(start_date, end_date)
    
    if df_readiness.empty:
        st.warning("No readiness data available for the selected date range.")
        return
    
    # Readiness metrics
    render_readiness_metrics(df_readiness, df_stress)
    
    st.markdown("---")
    
    # Readiness visualizations
    tab1, tab2, tab3 = st.tabs(["Readiness Trends", "Recovery Factors", "Stress Analysis"])
    
    with tab1:
        render_readiness_trends_tab(df_readiness)
    
    with tab2:
        render_recovery_factors_tab(df_readiness)
    
    with tab3:
        render_stress_analysis_tab(df_stress)
    
    # Recovery recommendations
    render_recovery_recommendations(df_readiness, df_stress)

def render_readiness_trends_tab(df_readiness):
    """Render readiness trends visualizations"""
    # Readiness score trend
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_readiness['date'],
        y=df_readiness['readiness_score'],
        mode='lines+markers',
        name='Readiness Score',
        line=dict(color=COLORS['activity'], width=3),
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
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True)
    
    # Contributors breakdown
    render_readiness_contributors(df_readiness)

def render_readiness_contributors(df_readiness):
    """Render readiness score contributors"""
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
            labels={'x': 'Score', 'y': 'Contributor'},
            color=contrib_data.values,
            color_continuous_scale='RdYlGn'
        )
        fig_contrib.update_traces(marker_line_width=0)
        st.plotly_chart(apply_chart_theme(fig_contrib), use_container_width=True)
        
        # Insights on contributors
        lowest_contributor = contrib_data.idxmin()
        highest_contributor = contrib_data.idxmax()
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💪 **Strongest Factor:** {highest_contributor} ({contrib_data[highest_contributor]:.0f})")
        with col2:
            st.warning(f"⚠️ **Needs Attention:** {lowest_contributor} ({contrib_data[lowest_contributor]:.0f})")

def render_recovery_factors_tab(df_readiness):
    """Render recovery factors analysis"""
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
            fig_hrv.update_traces(line_color=COLORS['readiness'], line_width=3)
            st.plotly_chart(apply_chart_theme(fig_hrv), use_container_width=True)
    
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
            fig_rhr.update_traces(line_color=COLORS['error'], line_width=3)
            st.plotly_chart(apply_chart_theme(fig_rhr), use_container_width=True)
    
    # Temperature deviation
    if 'temperature_deviation' in df_readiness.columns:
        render_temperature_analysis(df_readiness)
    
    # Recovery index analysis
    if 'recovery_index' in df_readiness.columns:
        render_recovery_index_analysis(df_readiness)

def render_temperature_analysis(df_readiness):
    """Render body temperature deviation analysis"""
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
    st.plotly_chart(apply_chart_theme(fig_temp), use_container_width=True)
    
    # Temperature insights
    avg_deviation = df_readiness['temperature_deviation'].mean()
    recent_deviation = df_readiness['temperature_deviation'].tail(3).mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Deviation", f"{avg_deviation:.2f}°C")
    with col2:
        if abs(recent_deviation) > 0.5:
            st.warning(f"Recent Deviation: {recent_deviation:.2f}°C - Monitor closely")
        else:
            st.success(f"Recent Deviation: {recent_deviation:.2f}°C - Normal range")

def render_recovery_index_analysis(df_readiness):
    """Render recovery index analysis"""
    st.subheader("Recovery Index")
    
    # Calculate recovery score
    recovery_score = calculate_recovery_score(df_readiness)
    
    # Create gauge
    fig_gauge = create_readiness_gauge(recovery_score)
    st.plotly_chart(fig_gauge, use_container_width=True)

def render_stress_analysis_tab(df_stress):
    """Render stress analysis visualizations"""
    if df_stress.empty:
        st.info("No stress data available for this period")
        return
    
    st.subheader("Stress & Recovery Balance")
    
    # Stress vs Recovery chart
    fig_stress = create_stress_recovery_chart(df_stress)
    st.plotly_chart(fig_stress, use_container_width=True)
    
    # Stress insights
    render_stress_insights(df_stress)
    
    # Daily stress patterns
    render_daily_stress_patterns(df_stress)

def render_stress_insights(df_stress):
    """Render stress insights and metrics"""
    avg_stress_min = df_stress['stress_high_minutes'].mean()
    avg_recovery_min = df_stress['recovery_high_minutes'].mean()
    avg_ratio = df_stress['stress_recovery_ratio'].mean()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Daily Averages")
        st.info(f"😰 Stress: {avg_stress_min:.0f} min")
        st.success(f"😌 Recovery: {avg_recovery_min:.0f} min")
    
    with col2:
        st.markdown("### Balance Status")
        if avg_ratio > 1.5:
            st.error("High stress - needs more recovery")
        elif avg_ratio > 1:
            st.warning("Moderate stress - monitor closely")
        else:
            st.success("Good balance!")
    
    with col3:
        st.markdown("### Stress Ratio")
        ratio_color = "🔴" if avg_ratio > 1.5 else "🟡" if avg_ratio > 1 else "🟢"
        st.metric(
            "Stress/Recovery Ratio",
            f"{avg_ratio:.2f}",
            f"{ratio_color} {'High' if avg_ratio > 1.5 else 'Moderate' if avg_ratio > 1 else 'Low'}"
        )

def render_daily_stress_patterns(df_stress):
    """Render daily stress patterns analysis"""
    st.subheader("Stress Patterns")
    
    # Add day of week
    df_stress['day_of_week'] = pd.to_datetime(df_stress['date']).dt.day_name()
    
    # Group by day of week
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_stress = df_stress.groupby('day_of_week')['stress_recovery_ratio'].mean().reindex(day_order)
    
    fig_dow = px.bar(
        x=dow_stress.index,
        y=dow_stress.values,
        title='Average Stress Ratio by Day of Week',
        labels={'x': 'Day', 'y': 'Stress/Recovery Ratio'},
        color=dow_stress.values,
        color_continuous_scale='Reds'
    )
    fig_dow.add_hline(y=1, line_dash="dash", line_color="gray", annotation_text="Balanced")
    
    st.plotly_chart(apply_chart_theme(fig_dow), use_container_width=True)

def render_recovery_recommendations(df_readiness, df_stress):
    """Render recovery recommendations"""
    st.subheader("💡 Recovery Recommendations")
    
    # Get recommendations
    recommendations = RecommendationEngine.get_readiness_recommendations(df_readiness, df_stress)
    
    if recommendations:
        # Prioritize and display
        top_recommendations = RecommendationEngine.prioritize_recommendations(recommendations, max_recommendations=5)
        
        for rec in top_recommendations:
            formatted_rec = RecommendationEngine.format_recommendation(rec)
            if rec['priority'] == 'high':
                st.error(formatted_rec)
            elif rec['priority'] == 'medium':
                st.warning(formatted_rec)
            else:
                st.info(formatted_rec)
    else:
        st.success("🎉 Your recovery status looks excellent! Keep maintaining this balance.")
    
    # Recovery tips
    with st.expander("🧘 Recovery & Stress Management Tips"):
        st.markdown("""
        **Improve Recovery:**
        - 😴 Prioritize quality sleep (7-9 hours)
        - 💧 Stay well hydrated
        - 🥗 Eat nutrient-dense foods
        - 🧘 Practice meditation or deep breathing
        - 🏃 Active recovery (light exercise)
        - 🛁 Take warm baths or saunas
        - 📱 Limit screen time before bed
        - 🎵 Listen to calming music
        
        **Manage Stress:**
        - 🧘‍♂️ Daily meditation (10-15 minutes)
        - 📝 Journal your thoughts
        - 🌳 Spend time in nature
        - 👥 Connect with loved ones
        - 🎨 Engage in creative activities
        - 📵 Digital detox periods
        - ☕ Limit caffeine intake
        - 🏋️ Regular exercise (but not excessive)
        """)