"""
Oura Health Dashboard - Main Application Entry Point
"""
import streamlit as st
from datetime import datetime
# Import configuration
from config import get_database_connection_string

# Import queries
from queries import OuraDataQueries

# Import UI components
from styles.custom_css import apply_custom_styles
from components.sidebar import render_sidebar
from ui_config import APP_TITLE, APP_ICON

# Import pages
from pages.overview import render_overview_page
from pages.sleep_analysis import render_sleep_analysis_page
from pages.activity_tracking import render_activity_tracking_page
from pages.readiness_recovery import render_readiness_recovery_page
from pages.trends_insights import render_trends_insights_page
from pages.heart_rate_analysis import render_heart_rate_analysis_page
from pages.advanced_metrics import render_advanced_metrics_page
from pages.detailed_reports import render_detailed_reports_page

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
apply_custom_styles()



# Initialize session state
if 'queries' not in st.session_state:
    try:
        connection_string = get_database_connection_string()
        st.session_state.queries = OuraDataQueries(connection_string)
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()

# Render sidebar and get navigation state
page, start_date, end_date, personal_info = render_sidebar(st.session_state.queries)

# Page routing
page_routes = {
    "Overview": render_overview_page,
    "Sleep Analysis": render_sleep_analysis_page,
    "Activity Tracking": render_activity_tracking_page,
    "Heart Rate Analysis": render_heart_rate_analysis_page,
    "Readiness & Recovery": render_readiness_recovery_page,
    "Advanced Metrics": render_advanced_metrics_page,
    "Trends & Insights": render_trends_insights_page,
    "Detailed Reports": render_detailed_reports_page
}

# Render selected page
if page in page_routes:
    page_routes[page](st.session_state.queries, start_date, end_date, personal_info)
else:
    st.error(f"Page '{page}' not found")

# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; padding: 20px;'>
        {APP_TITLE} | Data Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} | Made with ❤️ and Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
