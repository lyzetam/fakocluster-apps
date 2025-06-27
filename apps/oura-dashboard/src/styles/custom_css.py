"""
Custom CSS styles for Oura Health Dashboard
"""
import streamlit as st

def apply_custom_styles():
    """Apply all custom CSS styles to the dashboard"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)

def get_custom_css():
    """Return the custom CSS as a string"""
    return """
    <style>
        /* Metric Cards */
        .metric-card {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Typography */
        .big-font {
            font-size: 24px !important;
            font-weight: bold;
        }
        
        .medium-font {
            font-size: 18px !important;
        }
        
        .small-font {
            font-size: 14px !important;
        }
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 16px;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        
        .stTabs [data-baseweb="tab-list"] button {
            padding: 10px 20px;
        }
        
        /* Metrics Styling */
        [data-testid="metric-container"] {
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Headers */
        h1 {
            color: #262730;
            padding-bottom: 10px;
            border-bottom: 2px solid #45B7D1;
            margin-bottom: 20px;
        }
        
        h2 {
            color: #262730;
            margin-top: 20px;
            margin-bottom: 15px;
        }
        
        h3 {
            color: #262730;
            margin-top: 15px;
            margin-bottom: 10px;
        }
        
        /* Sidebar Styling */
        .css-1d391kg {
            padding-top: 2rem;
        }
        
        /* Charts Container */
        .chart-container {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        
        /* Info/Warning/Error Messages */
        .stAlert {
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #45B7D1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            background-color: #3A9BBF;
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        /* Select boxes */
        .stSelectbox > div > div {
            border-radius: 8px;
        }
        
        /* Date inputs */
        .stDateInput > div > div {
            border-radius: 8px;
        }
        
        /* Columns gap */
        [data-testid="column"] {
            padding: 0 10px;
        }
        
        /* Custom classes for specific elements */
        .health-score-excellent {
            color: #28a745;
            font-weight: bold;
        }
        
        .health-score-good {
            color: #ffc107;
            font-weight: bold;
        }
        
        .health-score-poor {
            color: #dc3545;
            font-weight: bold;
        }
        
        /* Loading spinner */
        .stSpinner > div {
            border-color: #45B7D1;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .metric-card {
                padding: 15px;
            }
            
            h1 {
                font-size: 24px;
            }
            
            h2 {
                font-size: 20px;
            }
        }
    </style>
    """

def get_metric_card_style(metric_type: str = "default"):
    """Get specific styles for metric cards based on type"""
    base_style = """
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    """
    
    type_styles = {
        "sleep": "border-left: 4px solid #4ECDC4;",
        "activity": "border-left: 4px solid #45B7D1;",
        "readiness": "border-left: 4px solid #96CEB4;",
        "overall": "border-left: 4px solid #FF6B6B;",
        "default": ""
    }
    
    return base_style + type_styles.get(metric_type, "")

def apply_chart_theme(fig):
    """Apply consistent theme to plotly charts"""
    fig.update_layout(
        font=dict(family="sans-serif", size=12, color="#262730"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=40, t=40, b=40),
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="sans-serif"
        )
    )
    return fig