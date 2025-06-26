"""
UI Configuration for Oura Health Dashboard
Centralized location for all UI elements, icons, and styling constants
"""

# App Configuration
APP_TITLE = "Oura Health Dashboard"
APP_ICON = "❤️"  # Main app icon - can be emoji, path to file, or URL

# Navigation Icons
NAV_ICONS = {
    "sidebar_title": "❤️",
    "overview": "📊",
    "sleep": "🌙", 
    "activity": "🏃",
    "readiness": "💪",
    "trends": "📈",
    "reports": "📋"
}

# Section Icons
SECTION_ICONS = {
    "health_score": "💚",
    "sleep_analysis": "😴",
    "activity_tracking": "🏃‍♂️",
    "readiness_recovery": "🔋",
    "trends_insights": "📊",
    "detailed_reports": "📑",
    "workouts": "🏋️",
    "stress": "🧘",
    "heart_rate": "💓",
    "temperature": "🌡️",
    "recommendations": "💡",
    "alerts": "🚨",
    "errors": "⚠️"
}

# Metric Icons  
METRIC_ICONS = {
    "steps": "👟",
    "calories": "🔥",
    "distance": "📏",
    "time": "⏱️",
    "efficiency": "⚡",
    "hrv": "💗",
    "heart_rate": "❤️",
    "temperature": "🌡️",
    "sleep_duration": "⏰",
    "deep_sleep": "💤",
    "rem_sleep": "🧠",
    "light_sleep": "😴"
}

# Status Indicators
STATUS_ICONS = {
    "good": "✅",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️",
    "success": "🎉",
    "loading": "⏳",
    "refresh": "🔄"
}

# Colors (for consistency)
COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4", 
    "success": "#95E1D3",
    "warning": "#F38181",
    "error": "#AA2E25",
    "sleep": "#4ECDC4",
    "activity": "#45B7D1",
    "readiness": "#96CEB4",
    "overall": "#FF6B6B"
}

# Chart Colors
CHART_COLORS = {
    "sleep_stages": {
        "deep": "#1f77b4",
        "rem": "#ff7f0e",
        "light": "#2ca02c",
        "awake": "#d62728"
    },
    "activity_levels": {
        "high": "#ff6b6b",
        "medium": "#ffd93d",
        "low": "#6bcf7f",
        "sedentary": "#a8a8a8"
    }
}

# Text Templates
TEMPLATES = {
    "no_data": "No {data_type} data available for this period",
    "loading": "Loading {data_type}...",
    "error": "Error loading {data_type}: {error}",
    "recommendation": "{icon} **{title}**: {description}"
}

# Helper Functions
def get_nav_title(page: str) -> str:
    """Get navigation title with icon"""
    icon = NAV_ICONS.get(page.lower().replace(" ", "_"), "")
    return f"{icon} {page}" if icon else page

def get_metric_display(metric: str, value: any, unit: str = "") -> str:
    """Format metric with icon"""
    icon = METRIC_ICONS.get(metric.lower(), "")
    return f"{icon} {value}{unit}" if icon else f"{value}{unit}"

def get_status_icon(status: str) -> str:
    """Get status icon"""
    return STATUS_ICONS.get(status.lower(), "")

def get_section_header(section: str) -> str:
    """Get section header with icon"""
    icon = SECTION_ICONS.get(section.lower().replace(" ", "_"), "")
    return f"{icon} {section}" if icon else section