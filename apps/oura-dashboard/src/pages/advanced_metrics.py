"""
Advanced Health Metrics page for Oura Health Dashboard
Displays VO2 Max, Cardiovascular Age, Resilience, SpO2, and other advanced metrics
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

def render_advanced_metrics_page(queries, start_date, end_date, personal_info):
    """Render the advanced health metrics page"""
    st.title("Advanced Health Metrics")
    st.markdown(f"**Date Range:** {start_date} to {end_date}")
    
    # Create tabs for different metric categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Fitness Metrics", "Blood Oxygen", "Resilience", "Sessions & Tags", "Device Info"
    ])
    
    with tab1:
        render_fitness_metrics(queries, start_date, end_date, personal_info)
    
    with tab2:
        render_blood_oxygen_metrics(queries, start_date, end_date)
    
    with tab3:
        render_resilience_metrics(queries, start_date, end_date)
    
    with tab4:
        render_sessions_and_tags(queries, start_date, end_date)
    
    with tab5:
        render_device_info(queries)

def render_fitness_metrics(queries, start_date, end_date, personal_info):
    """Render VO2 Max and Cardiovascular Age metrics"""
    st.subheader("Fitness & Cardiovascular Health")
    
    col1, col2 = st.columns(2)
    
    # VO2 Max
    with col1:
        df_vo2_max = queries.get_vo2_max_df(start_date, end_date)
        if not df_vo2_max.empty and 'vo2_max' in df_vo2_max.columns:
            latest_vo2_max = df_vo2_max.iloc[-1]['vo2_max']
            st.metric(
                "Current VO2 Max",
                f"{latest_vo2_max:.1f} mL/kg/min",
                help="Maximum oxygen consumption during exercise"
            )
            
            # VO2 Max trend chart
            fig_vo2 = go.Figure()
            fig_vo2.add_trace(go.Scatter(
                x=df_vo2_max['date'],
                y=df_vo2_max['vo2_max'],
                mode='lines+markers',
                name='VO2 Max',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(size=6)
            ))
            
            # Add fitness level zones
            age = personal_info.get('age', 30)
            fitness_zones = get_vo2_max_zones(age, personal_info.get('biological_sex', 'male'))
            for zone in fitness_zones:
                fig_vo2.add_hline(
                    y=zone['value'], 
                    line_dash="dash", 
                    line_color=zone['color'],
                    annotation_text=zone['label'],
                    annotation_position="right"
                )
            
            fig_vo2.update_layout(
                title="VO2 Max Trend",
                xaxis_title="Date",
                yaxis_title="VO2 Max (mL/kg/min)",
                height=300,
                showlegend=False
            )
            st.plotly_chart(fig_vo2, use_container_width=True)
        else:
            st.info("No VO2 Max data available for the selected period")
    
    # Cardiovascular Age
    with col2:
        df_cardio_age = queries.get_cardiovascular_age_df(start_date, end_date)
        if not df_cardio_age.empty and 'cardiovascular_age' in df_cardio_age.columns:
            latest_cardio_age = df_cardio_age.iloc[-1]['cardiovascular_age']
            actual_age = personal_info.get('age', 0)
            age_diff = latest_cardio_age - actual_age if actual_age else 0
            
            st.metric(
                "Cardiovascular Age",
                f"{latest_cardio_age} years",
                f"{age_diff:+.0f} vs actual age" if actual_age else None,
                delta_color="inverse"  # Lower is better
            )
            
            # Cardiovascular age trend chart
            fig_cardio = go.Figure()
            fig_cardio.add_trace(go.Scatter(
                x=df_cardio_age['date'],
                y=df_cardio_age['cardiovascular_age'],
                mode='lines+markers',
                name='Cardiovascular Age',
                line=dict(color='#4ECDC4', width=2),
                marker=dict(size=6)
            ))
            
            # Add actual age line
            if actual_age:
                fig_cardio.add_hline(
                    y=actual_age,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Actual Age: {actual_age}",
                    annotation_position="right"
                )
            
            fig_cardio.update_layout(
                title="Cardiovascular Age Trend",
                xaxis_title="Date",
                yaxis_title="Age (years)",
                height=300,
                showlegend=False
            )
            st.plotly_chart(fig_cardio, use_container_width=True)
        else:
            st.info("No Cardiovascular Age data available for the selected period")

def render_blood_oxygen_metrics(queries, start_date, end_date):
    """Render SpO2 and breathing metrics"""
    st.subheader("Blood Oxygen & Breathing")
    
    df_spo2 = queries.get_spo2_df(start_date, end_date)
    
    if not df_spo2.empty:
        col1, col2, col3 = st.columns(3)
        
        # Average SpO2
        with col1:
            if 'spo2_percentage_avg' in df_spo2.columns:
                avg_spo2 = df_spo2['spo2_percentage_avg'].mean()
                st.metric(
                    "Average SpO2",
                    f"{avg_spo2:.1f}%",
                    help="Blood oxygen saturation level"
                )
        
        # Breathing Disturbance Index
        with col2:
            if 'breathing_disturbance_index' in df_spo2.columns:
                avg_bdi = df_spo2['breathing_disturbance_index'].mean()
                st.metric(
                    "Avg Breathing Disturbance",
                    f"{avg_bdi:.2f}",
                    help="Average breathing disturbances per hour"
                )
        
        # Days with low SpO2
        with col3:
            if 'spo2_percentage_avg' in df_spo2.columns:
                low_spo2_days = len(df_spo2[df_spo2['spo2_percentage_avg'] < 95])
                st.metric(
                    "Days Below 95% SpO2",
                    low_spo2_days,
                    help="Number of days with SpO2 below 95%"
                )
        
        # SpO2 trend chart
        if 'spo2_percentage_avg' in df_spo2.columns:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("Blood Oxygen Saturation", "Breathing Disturbance Index"),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            # SpO2 trend
            fig.add_trace(
                go.Scatter(
                    x=df_spo2['date'],
                    y=df_spo2['spo2_percentage_avg'],
                    mode='lines+markers',
                    name='SpO2',
                    line=dict(color='#FF6B6B', width=2),
                    marker=dict(size=6)
                ),
                row=1, col=1
            )
            
            # Add normal range
            fig.add_hline(y=95, line_dash="dash", line_color="green", 
                         annotation_text="Normal (>95%)", row=1, col=1)
            fig.add_hline(y=90, line_dash="dash", line_color="orange", 
                         annotation_text="Low (<90%)", row=1, col=1)
            
            # Breathing disturbance index
            if 'breathing_disturbance_index' in df_spo2.columns:
                fig.add_trace(
                    go.Bar(
                        x=df_spo2['date'],
                        y=df_spo2['breathing_disturbance_index'],
                        name='Breathing Disturbance',
                        marker_color='#4ECDC4'
                    ),
                    row=2, col=1
                )
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="SpO2 (%)", row=1, col=1)
            fig.update_yaxes(title_text="Disturbances/hr", row=2, col=1)
            
            fig.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No SpO2 data available for the selected period")

def render_resilience_metrics(queries, start_date, end_date):
    """Render resilience metrics"""
    st.subheader("Resilience & Recovery Capacity")
    
    df_resilience = queries.get_resilience_df(start_date, end_date)
    
    if not df_resilience.empty and 'resilience_level' in df_resilience.columns:
        # Current resilience
        latest_resilience = df_resilience.iloc[-1]['resilience_level']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Current Resilience",
                latest_resilience.title() if isinstance(latest_resilience, str) else latest_resilience,
                help="Your body's ability to recover from physical and mental stress"
            )
        
        # Resilience distribution
        if len(df_resilience) > 1:
            resilience_counts = df_resilience['resilience_level'].value_counts()
            
            # Pie chart for resilience distribution
            fig_pie = px.pie(
                values=resilience_counts.values,
                names=resilience_counts.index,
                title="Resilience Level Distribution",
                color_discrete_map={
                    'strong': '#2ECC71',
                    'solid': '#3498DB',
                    'adequate': '#F39C12',
                    'limited': '#E74C3C'
                }
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Resilience timeline
        fig_timeline = go.Figure()
        
        # Convert resilience levels to numeric for visualization
        resilience_numeric = df_resilience['resilience_level'].map({
            'limited': 1,
            'adequate': 2,
            'solid': 3,
            'strong': 4
        })
        
        fig_timeline.add_trace(go.Scatter(
            x=df_resilience['date'],
            y=resilience_numeric,
            mode='lines+markers',
            line=dict(color='#9B59B6', width=3),
            marker=dict(size=8),
            text=df_resilience['resilience_level'],
            hovertemplate='%{text}<br>%{x}<extra></extra>'
        ))
        
        fig_timeline.update_yaxis(
            tickmode='array',
            tickvals=[1, 2, 3, 4],
            ticktext=['Limited', 'Adequate', 'Solid', 'Strong'],
            range=[0.5, 4.5]
        )
        
        fig_timeline.update_layout(
            title="Resilience Level Over Time",
            xaxis_title="Date",
            yaxis_title="Resilience Level",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Rest mode periods
        df_rest_mode = queries.get_rest_mode_periods_df(start_date, end_date)
        if not df_rest_mode.empty:
            st.subheader("Rest Mode Periods")
            for _, period in df_rest_mode.iterrows():
                end_text = period['end_date'].strftime('%Y-%m-%d') if pd.notna(period['end_date']) else "Ongoing"
                st.info(f"**Rest Mode:** {period['start_date'].strftime('%Y-%m-%d')} to {end_text} - {period['rest_mode_state']}")
    else:
        st.info("No Resilience data available for the selected period")

def render_sessions_and_tags(queries, start_date, end_date):
    """Render sessions and tags data"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Meditation & Breathing Sessions")
        df_sessions = queries.get_sessions_df(start_date, end_date)
        
        if not df_sessions.empty:
            # Session statistics
            total_sessions = len(df_sessions)
            total_duration = df_sessions['duration_minutes'].sum() if 'duration_minutes' in df_sessions.columns else 0
            
            st.metric("Total Sessions", total_sessions)
            st.metric("Total Duration", f"{total_duration:.0f} minutes")
            
            # Sessions by type
            if 'type' in df_sessions.columns:
                session_types = df_sessions['type'].value_counts()
                fig_sessions = px.bar(
                    x=session_types.index,
                    y=session_types.values,
                    title="Sessions by Type",
                    labels={'x': 'Session Type', 'y': 'Count'}
                )
                st.plotly_chart(fig_sessions, use_container_width=True)
        else:
            st.info("No session data available")
    
    with col2:
        st.subheader("Tags & Events")
        df_tags = queries.get_tags_df(start_date, end_date)
        
        if not df_tags.empty:
            # Display tags
            for _, tag_row in df_tags.iterrows():
                tag_date = tag_row['date'].strftime('%Y-%m-%d')
                tags = tag_row.get('tags', '')
                tag_type = tag_row.get('tag_type', 'general')
                st.write(f"**{tag_date}** ({tag_type}): {tags}")
        else:
            st.info("No tags recorded for this period")
        
        # Sleep time recommendations
        st.subheader("Sleep Recommendations")
        df_sleep_rec = queries.get_sleep_time_recommendations_df(start_date, end_date)
        
        if not df_sleep_rec.empty:
            latest_rec = df_sleep_rec.iloc[-1]
            if 'recommendation' in latest_rec:
                st.info(f"**Latest recommendation:** {latest_rec['recommendation']}")
        else:
            st.info("No sleep recommendations available")

def render_device_info(queries):
    """Render device configuration information"""
    st.subheader("Ring Configuration")
    
    df_ring = queries.get_ring_configuration_df()
    
    if not df_ring.empty:
        latest_config = df_ring.iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Ring Details:**")
            st.write(f"- Color: {latest_config.get('color', 'N/A')}")
            st.write(f"- Design: {latest_config.get('design', 'N/A')}")
            st.write(f"- Size: {latest_config.get('size', 'N/A')}")
        
        with col2:
            st.write("**Technical Info:**")
            st.write(f"- Hardware: {latest_config.get('hardware_type', 'N/A')}")
            st.write(f"- Firmware: {latest_config.get('firmware_version', 'N/A')}")
            if 'set_up_at' in latest_config and pd.notna(latest_config['set_up_at']):
                st.write(f"- Setup Date: {latest_config['set_up_at'].strftime('%Y-%m-%d')}")
    else:
        st.info("No ring configuration data available")

def get_vo2_max_zones(age, sex):
    """Get VO2 Max fitness zones based on age and sex"""
    # Simplified fitness zones - can be expanded with more detailed tables
    if sex.lower() == 'female':
        if age < 30:
            return [
                {'label': 'Poor', 'value': 33, 'color': 'red'},
                {'label': 'Fair', 'value': 37, 'color': 'orange'},
                {'label': 'Good', 'value': 42, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 47, 'color': 'green'}
            ]
        elif age < 40:
            return [
                {'label': 'Poor', 'value': 31, 'color': 'red'},
                {'label': 'Fair', 'value': 35, 'color': 'orange'},
                {'label': 'Good', 'value': 40, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 45, 'color': 'green'}
            ]
        else:
            return [
                {'label': 'Poor', 'value': 28, 'color': 'red'},
                {'label': 'Fair', 'value': 32, 'color': 'orange'},
                {'label': 'Good', 'value': 37, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 42, 'color': 'green'}
            ]
    else:  # Male
        if age < 30:
            return [
                {'label': 'Poor', 'value': 38, 'color': 'red'},
                {'label': 'Fair', 'value': 44, 'color': 'orange'},
                {'label': 'Good', 'value': 51, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 56, 'color': 'green'}
            ]
        elif age < 40:
            return [
                {'label': 'Poor', 'value': 35, 'color': 'red'},
                {'label': 'Fair', 'value': 41, 'color': 'orange'},
                {'label': 'Good', 'value': 47, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 53, 'color': 'green'}
            ]
        else:
            return [
                {'label': 'Poor', 'value': 32, 'color': 'red'},
                {'label': 'Fair', 'value': 38, 'color': 'orange'},
                {'label': 'Good', 'value': 44, 'color': 'yellow'},
                {'label': 'Excellent', 'value': 50, 'color': 'green'}
            ]
