"""
Reporting utilities for Katikaa Health Monitor
Generates health reports and exports data in various formats
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from jinja2 import Template
import json

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate health reports and analytics summaries"""
    
    def __init__(self):
        self.report_templates = self._load_report_templates()
        
    def _load_report_templates(self) -> Dict[str, str]:
        """Load HTML templates for reports"""
        return {
            'daily': self._get_daily_template(),
            'weekly': self._get_weekly_template(),
            'monthly': self._get_monthly_template(),
            'custom': self._get_custom_template()
        }
    
    def generate_report(self, report_type: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a health report based on type"""
        try:
            if data is None:
                data = self._collect_report_data(report_type)
            
            template = Template(self.report_templates.get(report_type, self.report_templates['daily']))
            
            report_context = {
                'report_type': report_type.title(),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data': data,
                'summary': self._generate_summary(data),
                'alerts': data.get('alerts', []),
                'recommendations': self._generate_recommendations(data)
            }
            
            return template.render(**report_context)
            
        except Exception as e:
            logger.error(f"Error generating {report_type} report: {e}")
            return self._generate_error_report(str(e))
    
    def _collect_report_data(self, report_type: str) -> Dict[str, Any]:
        """Collect data for report generation"""
        try:
            # Import here to avoid circular imports
            from app.components.financial_health import FinancialHealthMonitor
            from app.components.platform_health import PlatformHealthMonitor
            from app.components.payment_health import PaymentHealthMonitor
            from app.components.api_health import APIHealthMonitor
            from app.components.predictions_health import PredictionsHealthMonitor
            from app.components.alerting import AlertingSystem
            
            # Initialize monitors
            financial_monitor = FinancialHealthMonitor()
            platform_monitor = PlatformHealthMonitor()
            payment_monitor = PaymentHealthMonitor()
            api_monitor = APIHealthMonitor()
            predictions_monitor = PredictionsHealthMonitor()
            alerting_system = AlertingSystem()
            
            # Collect data from all components
            data = {
                'financial': financial_monitor.get_comprehensive_data(),
                'platform': platform_monitor.get_comprehensive_data(),
                'payment': payment_monitor.get_comprehensive_data(),
                'api': api_monitor.get_comprehensive_data(),
                'predictions': predictions_monitor.get_comprehensive_data(),
                'alerts': alerting_system.get_active_alerts(),
                'health_scores': {
                    'financial': financial_monitor.get_health_score(),
                    'platform': platform_monitor.get_health_score(),
                    'payment': payment_monitor.get_health_score(),
                    'api': api_monitor.get_health_score(),
                    'predictions': predictions_monitor.get_health_score()
                }
            }
            
            # Calculate overall health score
            scores = list(data['health_scores'].values())
            data['overall_health'] = sum(scores) / len(scores) if scores else 0
            
            return data
            
        except Exception as e:
            logger.error(f"Error collecting report data: {e}")
            return {
                'error': str(e),
                'financial': {},
                'platform': {},
                'payment': {},
                'api': {},
                'predictions': {},
                'alerts': [],
                'health_scores': {},
                'overall_health': 0
            }
    
    def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for the report"""
        try:
            overall_health = data.get('overall_health', 0)
            alerts = data.get('alerts', [])
            health_scores = data.get('health_scores', {})
            
            # Determine health status
            if overall_health >= 80:
                health_status = "Excellent"
                health_color = "green"
            elif overall_health >= 60:
                health_status = "Good"
                health_color = "orange"
            else:
                health_status = "Needs Attention"
                health_color = "red"
            
            # Count alerts by severity
            critical_alerts = len([a for a in alerts if a.get('severity') == 'critical'])
            warning_alerts = len([a for a in alerts if a.get('severity') == 'warning'])
            
            # Find best and worst performing components
            best_component = max(health_scores.items(), key=lambda x: x[1]) if health_scores else ("N/A", 0)
            worst_component = min(health_scores.items(), key=lambda x: x[1]) if health_scores else ("N/A", 0)
            
            return {
                'overall_health': overall_health,
                'health_status': health_status,
                'health_color': health_color,
                'total_alerts': len(alerts),
                'critical_alerts': critical_alerts,
                'warning_alerts': warning_alerts,
                'best_component': best_component,
                'worst_component': worst_component,
                'components_count': len(health_scores)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                'overall_health': 0,
                'health_status': "Error",
                'health_color': "red",
                'total_alerts': 0,
                'critical_alerts': 0,
                'warning_alerts': 0,
                'best_component': ("N/A", 0),
                'worst_component': ("N/A", 0),
                'components_count': 0
            }
    
    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on health data"""
        recommendations = []
        
        try:
            health_scores = data.get('health_scores', {})
            alerts = data.get('alerts', [])
            
            # Overall health recommendations
            overall_health = data.get('overall_health', 0)
            if overall_health < 60:
                recommendations.append("🚨 Urgent: Overall system health is below acceptable levels. Immediate attention required.")
            elif overall_health < 80:
                recommendations.append("⚠️ Warning: System health needs improvement. Monitor closely and address issues.")
            
            # Component-specific recommendations
            for component, score in health_scores.items():
                if score < 50:
                    recommendations.append(f"🔴 Critical: {component.title()} health is critically low ({score:.1f}%). Investigate immediately.")
                elif score < 70:
                    recommendations.append(f"🟡 Attention: {component.title()} health needs improvement ({score:.1f}%).")
            
            # Alert-based recommendations
            critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
            if critical_alerts:
                recommendations.append(f"🚨 {len(critical_alerts)} critical alerts require immediate attention.")
            
            # Financial recommendations
            financial_data = data.get('financial', {})
            if financial_data.get('failed_rate', 0) > 10:
                recommendations.append("💳 High transaction failure rate detected. Review payment processing.")
            
            # Platform recommendations
            platform_data = data.get('platform', {})
            if platform_data.get('dau', 0) < 500:
                recommendations.append("👥 Low daily active users. Consider user engagement strategies.")
            
            # API recommendations
            api_data = data.get('api', {})
            if api_data.get('usage_percent', 0) > 85:
                recommendations.append("🔌 API usage approaching limits. Consider upgrading quota or optimizing calls.")
            
            # Default recommendation if all is well
            if not recommendations and overall_health >= 80:
                recommendations.append("✅ System is healthy! Continue monitoring and maintain current practices.")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("❌ Unable to generate recommendations due to data collection issues.")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def export_data(self, data: Dict[str, Any], format: str = 'json') -> str:
        """Export health data in specified format"""
        try:
            if format.lower() == 'json':
                return json.dumps(data, indent=2, default=str)
            elif format.lower() == 'csv':
                # Flatten data for CSV export
                flattened = self._flatten_dict(data)
                df = pd.DataFrame([flattened])
                return df.to_csv(index=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return f"Error exporting data: {e}"
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary for CSV export"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _generate_error_report(self, error_message: str) -> str:
        """Generate error report when data collection fails"""
        return f"""
        <html>
        <head><title>Health Monitor Report Error</title></head>
        <body>
            <h1 style="color: red;">Report Generation Error</h1>
            <p>Unable to generate health report due to the following error:</p>
            <p style="background-color: #f8f9fa; padding: 10px; border-left: 3px solid #dc3545;">
                {error_message}
            </p>
            <p><em>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </body>
        </html>
        """
    
    def _get_daily_template(self) -> str:
        """Get daily report HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Katikaa Health Monitor - {{ report_type }} Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }
                .header { background-color: #1f77b4; color: white; padding: 20px; border-radius: 5px; }
                .summary { background-color: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .component { background-color: white; margin: 10px 0; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .health-score { font-size: 2em; font-weight: bold; display: inline-block; margin-right: 20px; }
                .health-good { color: #28a745; }
                .health-warning { color: #ffc107; }
                .health-critical { color: #dc3545; }
                .alerts { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .recommendations { background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .metric { display: inline-block; margin: 10px 20px 10px 0; }
                .metric-label { font-weight: bold; color: #6c757d; }
                .metric-value { font-size: 1.2em; color: #495057; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Katikaa Health Monitor</h1>
                <h2>{{ report_type }} Report</h2>
                <p>Generated: {{ generated_at }}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Executive Summary</h2>
                <div class="health-score health-{{ summary.health_color }}">
                    {{ "%.1f"|format(summary.overall_health) }}%
                </div>
                <span style="font-size: 1.5em;">{{ summary.health_status }}</span>
                
                <div style="margin-top: 20px;">
                    <div class="metric">
                        <div class="metric-label">Components Monitored</div>
                        <div class="metric-value">{{ summary.components_count }}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Alerts</div>
                        <div class="metric-value">{{ summary.total_alerts }}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Critical Alerts</div>
                        <div class="metric-value">{{ summary.critical_alerts }}</div>
                    </div>
                </div>
                
                <p><strong>Best Performing:</strong> {{ summary.best_component[0].title() }} ({{ "%.1f"|format(summary.best_component[1]) }}%)</p>
                <p><strong>Needs Attention:</strong> {{ summary.worst_component[0].title() }} ({{ "%.1f"|format(summary.worst_component[1]) }}%)</p>
            </div>
            
            <div class="component">
                <h3>🏥 Component Health Scores</h3>
                {% for component, score in data.health_scores.items() %}
                <div style="margin: 10px 0;">
                    <strong>{{ component.title() }}:</strong> 
                    <span class="health-score {% if score >= 80 %}health-good{% elif score >= 60 %}health-warning{% else %}health-critical{% endif %}">
                        {{ "%.1f"|format(score) }}%
                    </span>
                </div>
                {% endfor %}
            </div>
            
            {% if alerts %}
            <div class="alerts">
                <h3>🚨 Active Alerts ({{ alerts|length }})</h3>
                {% for alert in alerts[:5] %}
                <div style="margin: 10px 0; padding: 10px; background-color: white; border-radius: 3px;">
                    <strong>{{ alert.severity.upper() }}:</strong> {{ alert.message }}
                    <br><small>Component: {{ alert.component }} | Metric: {{ alert.metric }}</small>
                </div>
                {% endfor %}
                {% if alerts|length > 5 %}
                <p><em>... and {{ alerts|length - 5 }} more alerts</em></p>
                {% endif %}
            </div>
            {% endif %}
            
            <div class="recommendations">
                <h3>💡 Recommendations</h3>
                {% for rec in recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </div>
            
            <div style="margin-top: 40px; padding: 20px; background-color: white; border-radius: 5px; text-align: center;">
                <p style="color: #6c757d;"><em>This report was automatically generated by Katikaa Health Monitor</em></p>
            </div>
        </body>
        </html>
        """
    
    def _get_weekly_template(self) -> str:
        """Get weekly report template (extends daily with trends)"""
        return self._get_daily_template()  # For now, use same template
    
    def _get_monthly_template(self) -> str:
        """Get monthly report template (extends daily with more analytics)"""
        return self._get_daily_template()  # For now, use same template
    
    def _get_custom_template(self) -> str:
        """Get custom report template"""
        return self._get_daily_template()  # For now, use same template
