"""
Sidebar component for Oura Health Dashboard
"""
import streamlit as st
from datetime import timedelta
from ui_config import NAV_ICONS, get_nav_title

def render_sidebar(queries):
    """
    Render the sidebar and return navigation state
    
    Returns:
        tuple: (selected_page, start_date, end_date, personal_info)
    """
    # Title with icon
    st.sidebar.title(f"{NAV_ICONS['sidebar_title']} Oura Health Dashboard")
    st.sidebar.markdown("---")
    
    # Date range selection
    min_date, max_date = queries.get_date_range()
    st.sidebar.subheader("Date Range")
    
    # Calculate default start date (30 days ago or min_date, whichever is later)
    default_start = max(max_date - timedelta(days=30), min_date)
    
    start_date = st.sidebar.date_input(
        "Start Date",
        value=default_start,
        min_value=min_date,
        max_value=max_date
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=max_date,
        min_value=start_date,
        max_value=max_date
    )
    
    # Personal info section
    personal_info = render_personal_info(queries)
    
    # Navigation
    st.sidebar.markdown("---")
    pages = [
        "Overview",
        "Sleep Analysis",
        "Activity Tracking",
        "Heart Rate Analysis",
        "Readiness & Recovery",
        "Trends & Insights",
        "Detailed Reports"
    ]
    
    # Create radio buttons with icons
    page_options = [get_nav_title(page) for page in pages]
    selected_index = st.sidebar.radio(
        "Navigation",
        range(len(pages)),
        format_func=lambda x: page_options[x],
        label_visibility="collapsed"
    )
    
    selected_page = pages[selected_index]
    
    # Additional sidebar features
    render_sidebar_footer()
    
    return selected_page, start_date, end_date, personal_info

def render_personal_info(queries):
    """Render personal information section in sidebar"""
    personal_info = queries.get_personal_info()
    
    if personal_info:
        st.sidebar.subheader("Personal Info")
        
        # Age
        if personal_info.get('age'):
            st.sidebar.text(f"Age: {personal_info['age']}")
        
        # BMI calculation
        if personal_info.get('height') and personal_info.get('weight'):
            bmi = calculate_bmi(personal_info['weight'], personal_info['height'])
            bmi_status = get_bmi_status(bmi)
            st.sidebar.text(f"BMI: {bmi:.1f} ({bmi_status})")
        
        # Biological sex
        if personal_info.get('biological_sex'):
            st.sidebar.text(f"Sex: {personal_info['biological_sex']}")
    
    return personal_info

def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI from weight and height"""
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)

def get_bmi_status(bmi):
    """Get BMI status category"""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def render_sidebar_footer():
    """Render sidebar footer with additional options"""
    st.sidebar.markdown("---")
    
    # Quick actions
    with st.sidebar.expander("Quick Actions"):
        if st.button("🔄 Refresh Data"):
            st.rerun()
        
        if st.button("📊 Export Report"):
            st.info("Export functionality coming soon!")
        
        if st.button("⚙️ Settings"):
            st.info("Settings page coming soon!")
    
    # Help section
    with st.sidebar.expander("Need Help?"):
        st.markdown("""
        - **Data not showing?** Check your date range
        - **Missing metrics?** Some data may not be available
        - **Questions?** Contact support
        """)
    
    # Version info
    st.sidebar.markdown("---")
    st.sidebar.caption("Dashboard v1.0.0")