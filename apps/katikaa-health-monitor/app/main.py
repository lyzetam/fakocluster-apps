"""
Main Streamlit application for Katikaa Health Monitor Dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.config import Config
from app.health_metrics import HealthMetrics
from app.components.financial_health import FinancialHealthMonitor
from app.components.platform_health import PlatformHealthMonitor
from app.components.payment_health import PaymentHealthMonitor
from app.components.api_health import APIHealthMonitor
from app.components.predictions_health import PredictionsHealthMonitor
from app.components.alerting import AlertingSystem
from data.database import DatabaseManager
from utils.charts import ChartUtils
from utils.reporting import ReportGenerator

# Page configuration
st.set_page_config(
    page_title="Katikaa Health Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .health-score {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
    }
    .health-good { color: #28a745; }
    .health-warning { color: #ffc107; }
    .health-critical { color: #dc3545; }
    .alert-banner {
        padding: 0.5rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    .alert-critical { background-color: #f8d7da; border: 1px solid #f5c6cb; }
    .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; }
    .alert-info { background-color: #d1ecf1; border: 1px solid #bee5eb; }
</style>
""", unsafe_allow_html=True)

class KatikaaHealthDashboard:
    """Main dashboard class for health monitoring"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.health_metrics = HealthMetrics()
        self.financial_monitor = FinancialHealthMonitor()
        self.platform_monitor = PlatformHealthMonitor()
        self.payment_monitor = PaymentHealthMonitor()
        self.api_monitor = APIHealthMonitor()
        self.predictions_monitor = PredictionsHealthMonitor()
        self.alerting_system = AlertingSystem()
        self.chart_utils = ChartUtils()
        self.report_generator = ReportGenerator()
        
    def run(self):
        """Main dashboard application"""
        
        # Header
        st.markdown('<div class="main-header">🚀 Katikaa Health Monitor</div>', 
                   unsafe_allow_html=True)
        
        # Sidebar
        self.render_sidebar()
        
        # Main content based on selection
        page = st.session_state.get('current_page', 'overview')
        
        if page == 'overview':
            self.render_overview()
        elif page == 'financial':
            self.render_financial_health()
        elif page == 'platform':
            self.render_platform_health()
        elif page == 'payments':
            self.render_payment_health()
        elif page == 'api':
            self.render_api_health()
        elif page == 'predictions':
            self.render_predictions_health()
        elif page == 'alerts':
            self.render_alerts()
        elif page == 'reports':
            self.render_reports()
    
    def render_sidebar(self):
        """Render sidebar navigation and controls"""
        with st.sidebar:
            st.image("https://via.placeholder.com/200x60/1f77b4/ffffff?text=KATIKAA", 
                    width=200)
            
            st.markdown("### Navigation")
            
            # Navigation buttons
            pages = {
                'overview': '📈 Overview',
                'financial': '💰 Financial Health',
                'platform': '👥 Platform Health', 
                'payments': '💳 Payment Health',
                'api': '🔌 API Health',
                'predictions': '🎯 Predictions Health',
                'alerts': '🚨 Alerts',
                'reports': '📊 Reports'
            }
            
            for page_key, page_name in pages.items():
                if st.button(page_name, key=f"nav_{page_key}"):
                    st.session_state.current_page = page_key
                    st.rerun()
            
            st.markdown("---")
            
            # Refresh controls
            st.markdown("### Controls")
            if st.button("🔄 Refresh Data"):
                self.refresh_data()
                st.success("Data refreshed!")
            
            # Time range selector
            st.markdown("### Time Range")
            time_range = st.selectbox(
                "Select time range:",
                ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom"]
            )
            
            if time_range == "Custom":
                start_date = st.date_input("Start Date")
                end_date = st.date_input("End Date")
                st.session_state.time_range = (start_date, end_date)
            else:
                st.session_state.time_range = time_range
            
            # Health thresholds
            st.markdown("### Alert Thresholds")
            warning_threshold = st.slider("Warning Threshold", 0, 100, 60)
            critical_threshold = st.slider("Critical Threshold", 0, 100, 80)
            
            st.session_state.warning_threshold = warning_threshold
            st.session_state.critical_threshold = critical_threshold
    
    def render_overview(self):
        """Render main overview dashboard"""
        
        # Overall health score
        overall_health = self.health_metrics.calculate_overall_health()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Health score display
            health_class = self.get_health_class(overall_health)
            st.markdown(f"""
            <div class="metric-card">
                <h3>Overall Health Score</h3>
                <div class="health-score {health_class}">{overall_health:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Active alerts count
            alerts = self.alerting_system.get_active_alerts()
            st.metric("Active Alerts", len(alerts), delta=None)
        
        with col3:
            # Last update time
            last_update = datetime.now().strftime("%H:%M:%S")
            st.metric("Last Update", last_update)
        
        # Health component breakdown
        st.markdown("### Health Components")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        components = [
            ("Financial", self.financial_monitor.get_health_score(), col1),
            ("Platform", self.platform_monitor.get_health_score(), col2),
            ("Payments", self.payment_monitor.get_health_score(), col3),
            ("API", self.api_monitor.get_health_score(), col4),
            ("Predictions", self.predictions_monitor.get_health_score(), col5)
        ]
        
        for name, score, col in components:
            with col:
                health_class = self.get_health_class(score)
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{name}</h4>
                    <div class="health-score {health_class}">{score:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Alerts banner
        self.render_alerts_banner()
        
        # Key metrics overview
        self.render_key_metrics_overview()
        
        # Health trends
        self.render_health_trends()
    
    def render_financial_health(self):
        """Render financial health monitoring page"""
        st.markdown("## 💰 Financial Health Monitor")
        
        # Get financial health data
        financial_data = self.financial_monitor.get_comprehensive_data()
        
        if financial_data:
            # Financial overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total User Funds (FCFA)", 
                         f"{financial_data['total_user_funds']:,.2f}")
            
            with col2:
                st.metric("Daily Transaction Volume", 
                         f"{financial_data['daily_volume']:,.2f}")
            
            with col3:
                st.metric("Failed Transaction Rate", 
                         f"{financial_data['failed_rate']:.2f}%")
            
            with col4:
                st.metric("Commission Revenue", 
                         f"{financial_data['commission_revenue']:,.2f}")
            
            # Financial health visualizations
            self.render_financial_charts(financial_data)
        
        else:
            st.error("Unable to load financial data. Please check database connection.")
    
    def render_platform_health(self):
        """Render platform health monitoring page"""
        st.markdown("## 👥 Platform Health Monitor")
        
        platform_data = self.platform_monitor.get_comprehensive_data()
        
        if platform_data:
            # Platform overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Daily Active Users", platform_data['dau'])
            
            with col2:
                st.metric("Monthly Active Users", platform_data['mau'])
            
            with col3:
                st.metric("Active Communities", platform_data['active_communities'])
            
            with col4:
                st.metric("Daily Predictions", platform_data['daily_predictions'])
            
            # Platform health visualizations
            self.render_platform_charts(platform_data)
        
        else:
            st.error("Unable to load platform data.")
    
    def render_payment_health(self):
        """Render payment health monitoring page"""
        st.markdown("## 💳 Payment Health Monitor")
        
        payment_data = self.payment_monitor.get_comprehensive_data()
        
        if payment_data:
            # Payment overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Fapshi Balance", f"{payment_data['balance']:,.2f} FCFA")
            
            with col2:
                st.metric("Success Rate", f"{payment_data['success_rate']:.2f}%")
            
            with col3:
                st.metric("Daily Volume", f"{payment_data['daily_volume']:,.2f}")
            
            with col4:
                st.metric("Failed Transactions", payment_data['failed_count'])
            
            # Payment health visualizations
            self.render_payment_charts(payment_data)
        
        else:
            st.error("Unable to load payment data.")
    
    def render_api_health(self):
        """Render API health monitoring page"""
        st.markdown("## 🔌 API Health Monitor")
        
        api_data = self.api_monitor.get_comprehensive_data()
        
        if api_data:
            # API overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("SportMonks Usage", f"{api_data['usage_percent']:.1f}%")
            
            with col2:
                st.metric("Daily API Calls", api_data['daily_calls'])
            
            with col3:
                st.metric("Error Rate", f"{api_data['error_rate']:.2f}%")
            
            with col4:
                st.metric("Avg Response Time", f"{api_data['avg_response_time']:.0f}ms")
            
            # API health visualizations
            self.render_api_charts(api_data)
        
        else:
            st.error("Unable to load API data.")
    
    def render_predictions_health(self):
        """Render predictions health monitoring page"""
        st.markdown("## 🎯 Predictions Health Monitor")
        
        predictions_data = self.predictions_monitor.get_comprehensive_data()
        
        if predictions_data:
            # Predictions overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Daily Predictions", predictions_data['daily_count'])
            
            with col2:
                st.metric("Accuracy Rate", f"{predictions_data['accuracy']:.2f}%")
            
            with col3:
                st.metric("Active Fixtures", predictions_data['active_fixtures'])
            
            with col4:
                st.metric("User Engagement", f"{predictions_data['engagement']:.1f}%")
            
            # Predictions health visualizations
            self.render_predictions_charts(predictions_data)
        
        else:
            st.error("Unable to load predictions data.")
    
    def render_alerts(self):
        """Render alerts page"""
        st.markdown("## 🚨 Active Alerts")
        
        alerts = self.alerting_system.get_active_alerts()
        
        if alerts:
            for alert in alerts:
                alert_class = f"alert-{alert['severity'].lower()}"
                st.markdown(f"""
                <div class="alert-banner {alert_class}">
                    <strong>{alert['severity'].upper()}:</strong> {alert['message']}
                    <br><small>Since: {alert['timestamp']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No active alerts! 🎉")
    
    def render_reports(self):
        """Render reports page"""
        st.markdown("## 📊 Health Reports")
        
        report_type = st.selectbox(
            "Select Report Type:",
            ["Daily Summary", "Weekly Report", "Monthly Report", "Custom"]
        )
        
        if st.button("Generate Report"):
            report = self.report_generator.generate_report(report_type)
            st.markdown(report, unsafe_allow_html=True)
    
    def render_alerts_banner(self):
        """Render alerts banner on overview"""
        alerts = self.alerting_system.get_critical_alerts()
        
        if alerts:
            for alert in alerts[:3]:  # Show top 3 critical alerts
                st.markdown(f"""
                <div class="alert-banner alert-critical">
                    🚨 <strong>CRITICAL:</strong> {alert['message']}
                </div>
                """, unsafe_allow_html=True)
    
    def render_key_metrics_overview(self):
        """Render key metrics overview"""
        st.markdown("### Key Metrics")
        
        # Create metrics grid
        metrics_data = self.health_metrics.get_key_metrics()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Financial metrics chart
            fig_financial = self.chart_utils.create_financial_overview_chart(
                metrics_data['financial']
            )
            st.plotly_chart(fig_financial, use_container_width=True)
        
        with col2:
            # User engagement chart
            fig_engagement = self.chart_utils.create_engagement_chart(
                metrics_data['engagement']
            )
            st.plotly_chart(fig_engagement, use_container_width=True)
    
    def render_health_trends(self):
        """Render health trends over time"""
        st.markdown("### Health Trends")
        
        trends_data = self.health_metrics.get_health_trends()
        
        fig = self.chart_utils.create_health_trends_chart(trends_data)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_financial_charts(self, data):
        """Render financial health specific charts"""
        # Implementation based on balances_analytics.ipynb logic
        pass
    
    def render_platform_charts(self, data):
        """Render platform health specific charts"""
        # Implementation based on katikaa_analytics.ipynb logic
        pass
    
    def render_payment_charts(self, data):
        """Render payment health specific charts"""
        # Implementation based on Fapshi_Workbook.ipynb logic
        pass
    
    def render_api_charts(self, data):
        """Render API health specific charts"""
        # Implementation based on sportmonks usage.ipynb logic
        pass
    
    def render_predictions_charts(self, data):
        """Render predictions health specific charts"""
        # Implementation based on predictions_analytics notebooks logic
        pass
    
    def get_health_class(self, score):
        """Get CSS class based on health score"""
        if score >= 80:
            return "health-good"
        elif score >= 60:
            return "health-warning"
        else:
            return "health-critical"
    
    def refresh_data(self):
        """Refresh all data sources"""
        try:
            self.health_metrics.refresh()
            self.financial_monitor.refresh()
            self.platform_monitor.refresh()
            self.payment_monitor.refresh()
            self.api_monitor.refresh()
            self.predictions_monitor.refresh()
        except Exception as e:
            st.error(f"Error refreshing data: {e}")

def main():
    """Main application entry point"""
    
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'overview'
    
    # Create and run dashboard
    dashboard = KatikaaHealthDashboard()
    
    try:
        dashboard.run()
    except Exception as e:
        st.error(f"Application error: {e}")
        st.markdown("Please check the logs and try refreshing the page.")

# Health check endpoint for Docker
@st.cache_data
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    main()
