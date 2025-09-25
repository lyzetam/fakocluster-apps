"""
Chart utilities for Katikaa Health Monitor
Creates interactive Plotly charts for health monitoring dashboard
"""

import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ChartUtils:
    """Utility class for creating charts and visualizations"""
    
    def __init__(self):
        # Default colors for consistency across charts
        self.colors = {
            'primary': '#1f77b4',
            'success': '#28a745',
            'warning': '#ffc107', 
            'danger': '#dc3545',
            'info': '#17a2b8',
            'secondary': '#6c757d'
        }
        
        self.chart_config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
        }
    
    def create_financial_overview_chart(self, financial_data: Dict[str, Any]) -> go.Figure:
        """Create financial overview chart"""
        try:
            # Create subplots for multiple metrics
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Total User Funds', 'Daily Volume', 'Transaction Success Rate', 'Commission Revenue'),
                specs=[[{"type": "indicator"}, {"type": "indicator"}],
                       [{"type": "indicator"}, {"type": "indicator"}]]
            )
            
            # Total User Funds gauge
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=financial_data.get('total_user_funds', 0),
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "FCFA"},
                    gauge={
                        'axis': {'range': [None, 5000000]},
                        'bar': {'color': self.colors['primary']},
                        'steps': [
                            {'range': [0, 2500000], 'color': "lightgray"},
                            {'range': [2500000, 5000000], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 4000000
                        }
                    }
                ),
                row=1, col=1
            )
            
            # Daily Volume
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=financial_data.get('daily_volume', 0),
                    title={'text': "Daily Volume (FCFA)"},
                    number={'prefix': "₣"},
                    delta={'position': "top", 'reference': financial_data.get('previous_volume', 0)}
                ),
                row=1, col=2
            )
            
            # Success Rate
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=financial_data.get('success_rate', 0),
                    title={'text': "Success Rate (%)"},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': self.colors['success']},
                        'steps': [
                            {'range': [0, 70], 'color': self.colors['danger']},
                            {'range': [70, 90], 'color': self.colors['warning']},
                            {'range': [90, 100], 'color': self.colors['success']}
                        ]
                    }
                ),
                row=2, col=1
            )
            
            # Commission Revenue
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=financial_data.get('commission_revenue', 0),
                    title={'text': "Commission Revenue (FCFA)"},
                    number={'prefix': "₣"},
                    delta={'position': "top", 'reference': financial_data.get('previous_commission', 0)}
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                title="Financial Health Overview",
                height=500,
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating financial overview chart: {e}")
            return self._create_error_chart("Error loading financial data")
    
    def create_engagement_chart(self, engagement_data: Dict[str, Any]) -> go.Figure:
        """Create user engagement chart"""
        try:
            fig = go.Figure()
            
            # Create donut chart for engagement metrics
            labels = ['Active Users', 'Inactive Users', 'New Users']
            values = [
                engagement_data.get('active_users', 0),
                engagement_data.get('inactive_users', 0),
                engagement_data.get('new_users', 0)
            ]
            colors = [self.colors['success'], self.colors['secondary'], self.colors['info']]
            
            fig.add_trace(go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker_colors=colors,
                textinfo='label+percent',
                textposition='outside'
            ))
            
            fig.update_layout(
                title="User Engagement Distribution",
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating engagement chart: {e}")
            return self._create_error_chart("Error loading engagement data")
    
    def create_health_trends_chart(self, trends_data: Dict[str, List]) -> go.Figure:
        """Create health trends over time chart"""
        try:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Overall Health Score', 'Component Health Scores'),
                shared_xaxes=True,
                vertical_spacing=0.1
            )
            
            dates = trends_data.get('dates', [])
            overall_health = trends_data.get('overall_health', [])
            
            # Overall health trend
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=overall_health,
                    mode='lines+markers',
                    name='Overall Health',
                    line=dict(color=self.colors['primary'], width=3),
                    marker=dict(size=6)
                ),
                row=1, col=1
            )
            
            # Component health trends
            components = ['Financial', 'Platform', 'Payment', 'API', 'Predictions']
            component_colors = [self.colors['success'], self.colors['info'], 
                              self.colors['warning'], self.colors['danger'], self.colors['secondary']]
            
            for i, component in enumerate(components):
                component_data = trends_data.get(component.lower(), [])
                if component_data:
                    fig.add_trace(
                        go.Scatter(
                            x=dates,
                            y=component_data,
                            mode='lines',
                            name=component,
                            line=dict(color=component_colors[i], width=2)
                        ),
                        row=2, col=1
                    )
            
            # Add threshold lines
            fig.add_hline(y=80, line_dash="dash", line_color="red", 
                         annotation_text="Critical Threshold", row=1, col=1)
            fig.add_hline(y=60, line_dash="dash", line_color="orange", 
                         annotation_text="Warning Threshold", row=1, col=1)
            
            fig.update_layout(
                title="Health Trends Over Time",
                height=600,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                hovermode='x unified'
            )
            
            fig.update_yaxes(title_text="Health Score (%)", range=[0, 100])
            fig.update_xaxes(title_text="Date", row=2, col=1)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating health trends chart: {e}")
            return self._create_error_chart("Error loading trends data")
    
    def create_transaction_volume_chart(self, volume_data: Dict[str, List]) -> go.Figure:
        """Create transaction volume chart"""
        try:
            fig = go.Figure()
            
            dates = volume_data.get('dates', [])
            volumes = volume_data.get('volumes', [])
            
            # Create bar chart for daily volumes
            fig.add_trace(go.Bar(
                x=dates,
                y=volumes,
                name='Daily Volume',
                marker_color=self.colors['primary'],
                hovertemplate='Date: %{x}<br>Volume: ₣%{y:,.2f}<extra></extra>'
            ))
            
            # Add trend line
            if len(volumes) > 1:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=self._calculate_moving_average(volumes, window=7),
                    mode='lines',
                    name='7-day Average',
                    line=dict(color=self.colors['danger'], width=3),
                    hovertemplate='Date: %{x}<br>7-day Avg: ₣%{y:,.2f}<extra></extra>'
                ))
            
            fig.update_layout(
                title="Daily Transaction Volume",
                xaxis_title="Date",
                yaxis_title="Volume (FCFA)",
                height=400,
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating transaction volume chart: {e}")
            return self._create_error_chart("Error loading volume data")
    
    def create_success_rate_chart(self, success_data: Dict[str, List]) -> go.Figure:
        """Create success rate trend chart"""
        try:
            fig = go.Figure()
            
            dates = success_data.get('dates', [])
            success_rates = success_data.get('success_rates', [])
            
            # Create line chart for success rates
            fig.add_trace(go.Scatter(
                x=dates,
                y=success_rates,
                mode='lines+markers',
                name='Success Rate',
                line=dict(color=self.colors['success'], width=3),
                marker=dict(size=6),
                fill='tonexty',
                hovertemplate='Date: %{x}<br>Success Rate: %{y:.1f}%<extra></extra>'
            ))
            
            # Add threshold lines
            fig.add_hline(y=95, line_dash="dash", line_color=self.colors['success'], 
                         annotation_text="Target (95%)")
            fig.add_hline(y=85, line_dash="dash", line_color=self.colors['warning'], 
                         annotation_text="Warning (85%)")
            
            fig.update_layout(
                title="Transaction Success Rate Trend",
                xaxis_title="Date",
                yaxis_title="Success Rate (%)",
                height=400,
                yaxis=dict(range=[0, 100])
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating success rate chart: {e}")
            return self._create_error_chart("Error loading success rate data")
    
    def create_api_usage_chart(self, api_data: Dict[str, Any]) -> go.Figure:
        """Create API usage chart"""
        try:
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('API Usage Distribution', 'Response Time Trend'),
                specs=[[{"type": "pie"}, {"type": "scatter"}]]
            )
            
            # API Usage pie chart
            endpoints = list(api_data.get('endpoint_usage', {}).keys())
            usage_counts = list(api_data.get('endpoint_usage', {}).values())
            
            fig.add_trace(
                go.Pie(
                    labels=endpoints,
                    values=usage_counts,
                    textinfo='label+percent',
                    showlegend=False
                ),
                row=1, col=1
            )
            
            # Response time trend
            dates = api_data.get('dates', [])
            response_times = api_data.get('response_times', [])
            
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=response_times,
                    mode='lines+markers',
                    name='Response Time',
                    line=dict(color=self.colors['info'], width=2),
                    marker=dict(size=4)
                ),
                row=1, col=2
            )
            
            fig.update_layout(
                title="API Health Metrics",
                height=400
            )
            
            fig.update_yaxes(title_text="Response Time (ms)", row=1, col=2)
            fig.update_xaxes(title_text="Date", row=1, col=2)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating API usage chart: {e}")
            return self._create_error_chart("Error loading API data")
    
    def create_prediction_accuracy_chart(self, prediction_data: Dict[str, Any]) -> go.Figure:
        """Create prediction accuracy chart by league"""
        try:
            leagues = list(prediction_data.get('accuracy_by_league', {}).keys())
            accuracies = list(prediction_data.get('accuracy_by_league', {}).values())
            
            # Create horizontal bar chart
            fig = go.Figure(go.Bar(
                x=accuracies,
                y=leagues,
                orientation='h',
                marker_color=self.colors['primary'],
                hovertemplate='League: %{y}<br>Accuracy: %{x:.1f}%<extra></extra>'
            ))
            
            # Add target line
            fig.add_vline(x=65, line_dash="dash", line_color=self.colors['warning'], 
                         annotation_text="Target (65%)")
            
            fig.update_layout(
                title="Prediction Accuracy by League",
                xaxis_title="Accuracy (%)",
                yaxis_title="League",
                height=400,
                xaxis=dict(range=[0, 100])
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating prediction accuracy chart: {e}")
            return self._create_error_chart("Error loading prediction data")
    
    def _calculate_moving_average(self, data: List[float], window: int = 7) -> List[float]:
        """Calculate moving average for trend lines"""
        if len(data) < window:
            return data
        
        moving_avg = []
        for i in range(len(data)):
            if i < window - 1:
                moving_avg.append(sum(data[:i+1]) / (i+1))
            else:
                moving_avg.append(sum(data[i-window+1:i+1]) / window)
        
        return moving_avg
    
    def _create_error_chart(self, error_message: str) -> go.Figure:
        """Create error chart when data loading fails"""
        fig = go.Figure()
        fig.add_annotation(
            text=error_message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color=self.colors['danger'])
        )
        fig.update_layout(
            title="Chart Error",
            height=300,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    def get_color_palette(self) -> Dict[str, str]:
        """Get the standard color palette"""
        return self.colors.copy()
    
    def update_chart_theme(self, theme: str = 'plotly_white'):
        """Update chart theme"""
        try:
            import plotly.io as pio
            pio.templates.default = theme
        except Exception as e:
            logger.error(f"Error updating chart theme: {e}")
