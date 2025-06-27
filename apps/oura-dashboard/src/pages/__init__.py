# pages/__init__.py
"""
Pages package for Oura Health Dashboard
"""
from .overview import render_overview_page
from .sleep_analysis import render_sleep_analysis_page
from .activity_tracking import render_activity_tracking_page
from .readiness_recovery import render_readiness_recovery_page
from .trends_insights import render_trends_insights_page
from .detailed_reports import render_detailed_reports_page
from .heart_rate_analysis import render_heart_rate_analysis_page


__all__ = [
    'render_overview_page',
    'render_sleep_analysis_page',
    'render_activity_tracking_page',
    'render_readiness_recovery_page',
    'render_trends_insights_page',
    'render_heart_rate_analysis_page',
    'render_detailed_reports_page'
]