
# components/__init__.py
"""
Components package for Oura Health Dashboard
"""
from .metrics import (
    render_metric_card,
    render_health_score_metrics,
    render_sleep_metrics,
    render_activity_metrics,
    render_readiness_metrics,
    render_workout_metrics,
    get_score_status,
    render_score_gauge
)

from .charts import (
    create_health_scores_chart,
    create_steps_chart,
    create_hrv_balance_chart,
    create_sleep_analysis_charts,
    create_sleep_stages_pie,
    create_activity_distribution_chart,
    create_readiness_gauge,
    create_correlation_heatmap,
    create_weekly_trends_chart,
    create_stress_recovery_chart
)

from .sidebar import render_sidebar, calculate_bmi, get_bmi_status

__all__ = [
    # Metrics
    'render_metric_card',
    'render_health_score_metrics',
    'render_sleep_metrics',
    'render_activity_metrics',
    'render_readiness_metrics',
    'render_workout_metrics',
    'get_score_status',
    'render_score_gauge',
    # Charts
    'create_health_scores_chart',
    'create_steps_chart',
    'create_hrv_balance_chart',
    'create_sleep_analysis_charts',
    'create_sleep_stages_pie',
    'create_activity_distribution_chart',
    'create_readiness_gauge',
    'create_correlation_heatmap',
    'create_weekly_trends_chart',
    'create_stress_recovery_chart',
    # Sidebar
    'render_sidebar',
    'calculate_bmi',
    'get_bmi_status'
]
