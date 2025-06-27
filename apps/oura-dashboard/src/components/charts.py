"""
Chart components for Oura Health Dashboard
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from ui_config import COLORS, CHART_COLORS
from styles.custom_css import apply_chart_theme

def create_health_scores_chart(df_summary):
    """Create line chart showing all health scores"""
    fig = go.Figure()
    
    # Add traces for each score type
    score_columns = [
        ('overall_health_score', 'Overall Health', COLORS['overall']),
        ('sleep_score', 'Sleep', COLORS['sleep']),
        ('activity_score', 'Activity', COLORS['activity']),
        ('readiness_score', 'Readiness', COLORS['readiness'])
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
    
    return apply_chart_theme(fig)

def create_steps_chart(df_summary):
    """Create bar chart for daily steps"""
    fig = px.bar(
        df_summary,
        x='date',
        y='steps',
        title='Daily Steps',
        color='steps',
        color_continuous_scale='Blues'
    )
    fig.add_hline(y=10000, line_dash="dash", 
                  annotation_text="10k Goal")
    fig.update_layout(height=350)
    return apply_chart_theme(fig)

def create_hrv_balance_chart(df_summary):
    """Create HRV balance trend chart"""
    fig = px.line(
        df_summary,
        x='date',
        y='hrv_balance',
        title='HRV Balance Trend',
        markers=True
    )
    fig.update_traces(line_color=COLORS['readiness'], line_width=3)
    fig.update_layout(height=350)
    return apply_chart_theme(fig)

def create_sleep_analysis_charts(df_main_sleep):
    """Create comprehensive sleep analysis charts"""
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Sleep Duration Trend', 'Sleep Stages Distribution',
                      'Sleep Efficiency', 'Heart Rate & HRV'),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    # 1. Sleep duration trend
    fig.add_trace(
        go.Scatter(
            x=df_main_sleep['date'],
            y=df_main_sleep['total_sleep_hours'],
            mode='lines+markers',
            name='Sleep Hours',
            line=dict(color=COLORS['sleep'], width=3)
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
            fillcolor=CHART_COLORS['sleep_stages']['deep']
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
            fillcolor=CHART_COLORS['sleep_stages']['rem']
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
            fillcolor=CHART_COLORS['sleep_stages']['light']
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
            line=dict(color=COLORS['readiness'], width=3)
        ),
        row=2, col=1
    )
    fig.add_hline(y=85, line_dash="dash", line_color="gray", 
                 row=2, col=1)
    
    # 4. Heart rate and HRV
    if 'heart_rate_avg' in df_main_sleep.columns and 'hrv_avg' in df_main_sleep.columns:
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['heart_rate_avg'],
                mode='lines+markers',
                name='Heart Rate',
                line=dict(color=COLORS['error'], width=2)
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_main_sleep['date'],
                y=df_main_sleep['hrv_avg'],
                mode='lines+markers',
                name='HRV',
                line=dict(color=COLORS['activity'], width=2),
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
    return apply_chart_theme(fig)

def create_sleep_stages_pie(df_main_sleep):
    """Create pie chart for average sleep stage distribution"""
    avg_stages = df_main_sleep[['rem_percentage', 'deep_percentage', 'light_percentage']].mean()
    
    fig = px.pie(
        values=avg_stages.values,
        names=['REM', 'Deep', 'Light'],
        title='Average Sleep Stage Distribution',
        color_discrete_map={
            'REM': CHART_COLORS['sleep_stages']['rem'],
            'Deep': CHART_COLORS['sleep_stages']['deep'],
            'Light': CHART_COLORS['sleep_stages']['light']
        }
    )
    return apply_chart_theme(fig)

def create_activity_distribution_chart(activity_dist):
    """Create pie chart for activity intensity distribution"""
    fig = px.pie(
        values=activity_dist.values,
        names=['High', 'Medium', 'Low'],
        title='Average Activity Intensity Distribution',
        color_discrete_map={
            'High': CHART_COLORS['activity_levels']['high'],
            'Medium': CHART_COLORS['activity_levels']['medium'],
            'Low': CHART_COLORS['activity_levels']['low']
        }
    )
    return apply_chart_theme(fig)

def create_readiness_gauge(recovery_score):
    """Create gauge chart for recovery status"""
    fig = go.Figure(go.Indicator(
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
    return apply_chart_theme(fig)

def create_correlation_heatmap(correlations):
    """Create correlation heatmap"""
    fig = px.imshow(
        correlations,
        labels=dict(color="Correlation"),
        x=correlations.columns,
        y=correlations.columns,
        color_continuous_scale='RdBu',
        zmin=-1, zmax=1,
        title="Correlation Matrix of Health Metrics"
    )
    fig.update_layout(height=600)
    return apply_chart_theme(fig)

def create_weekly_trends_chart(weekly_summary):
    """Create multi-line chart for weekly trends"""
    fig = go.Figure()
    
    metrics = ['sleep_score', 'activity_score', 'readiness_score', 'overall_health_score']
    colors = [COLORS['sleep'], COLORS['activity'], COLORS['readiness'], COLORS['overall']]
    
    for metric, color in zip(metrics, colors):
        if metric in weekly_summary.columns:
            fig.add_trace(go.Scatter(
                x=weekly_summary['week_start'],
                y=weekly_summary[metric],
                mode='lines+markers',
                name=metric.replace('_', ' ').title(),
                line=dict(color=color, width=3),
                marker=dict(size=8)
            ))
    
    fig.update_layout(
        title="Weekly Average Scores",
        xaxis_title="Week Starting",
        yaxis_title="Score",
        height=400,
        hovermode='x unified',
        yaxis=dict(range=[0, 100])
    )
    return apply_chart_theme(fig)

def create_stress_recovery_chart(df_stress):
    """Create stress vs recovery chart"""
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
            marker_color=COLORS['error']
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_stress['date'],
            y=df_stress['recovery_high_minutes'],
            name='Recovery Minutes',
            marker_color=COLORS['success']
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
            line=dict(color=COLORS['warning'], width=3)
        ),
        row=2, col=1
    )
    
    fig.add_hline(y=1, line_dash="dash", line_color="gray", 
                annotation_text="Balanced", row=2, col=1)
    
    fig.update_layout(height=600, showlegend=True)
    return apply_chart_theme(fig)