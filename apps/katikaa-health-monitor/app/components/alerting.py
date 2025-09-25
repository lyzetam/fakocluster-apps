"""
Alerting System Component
Manages health alerts, notifications, and alert thresholds across all monitoring components
"""

import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from app.config import config

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertingSystem:
    """Centralized alerting system for health monitoring"""
    
    def __init__(self):
        self.config = config
        self.active_alerts = []
        self._load_alert_thresholds()
        
    def _load_alert_thresholds(self):
        """Load alert thresholds from configuration"""
        self.thresholds = self.config.get_alert_thresholds()
        
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active alerts"""
        try:
            # In a real implementation, this would query a database or cache
            # For now, return the in-memory active alerts
            return self.active_alerts
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    def get_critical_alerts(self) -> List[Dict[str, Any]]:
        """Get only critical severity alerts"""
        try:
            return [
                alert for alert in self.active_alerts 
                if alert.get('severity') == AlertSeverity.CRITICAL.value
            ]
        except Exception as e:
            logger.error(f"Error getting critical alerts: {e}")
            return []
    
    def add_alert(self, component: str, metric: str, message: str, 
                 severity: AlertSeverity, value: Any = None, threshold: Any = None) -> bool:
        """Add a new alert to the system"""
        try:
            alert = {
                'id': self._generate_alert_id(component, metric),
                'component': component,
                'metric': metric,
                'message': message,
                'severity': severity.value,
                'value': value,
                'threshold': threshold,
                'timestamp': datetime.now().isoformat(),
                'acknowledged': False
            }
            
            # Check if alert already exists
            existing_alert = self._find_existing_alert(component, metric)
            if existing_alert:
                # Update existing alert
                existing_alert.update(alert)
                logger.info(f"Updated existing alert: {component}/{metric}")
            else:
                # Add new alert
                self.active_alerts.append(alert)
                logger.info(f"Added new alert: {component}/{metric} - {severity.value}")
                
                # Send notifications for new alerts
                if severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
                    self._send_notification(alert)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding alert: {e}")
            return False
    
    def resolve_alert(self, component: str, metric: str) -> bool:
        """Resolve an active alert"""
        try:
            alert_id = self._generate_alert_id(component, metric)
            self.active_alerts = [
                alert for alert in self.active_alerts 
                if alert.get('id') != alert_id
            ]
            logger.info(f"Resolved alert: {component}/{metric}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            for alert in self.active_alerts:
                if alert.get('id') == alert_id:
                    alert['acknowledged'] = True
                    alert['acknowledged_at'] = datetime.now().isoformat()
                    logger.info(f"Acknowledged alert: {alert_id}")
                    return True
            
            logger.warning(f"Alert not found for acknowledgment: {alert_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def check_all_health_components(self):
        """Check all health components and generate alerts"""
        try:
            # Import here to avoid circular imports
            from app.components.financial_health import FinancialHealthMonitor
            from app.components.platform_health import PlatformHealthMonitor
            from app.components.payment_health import PaymentHealthMonitor
            from app.components.api_health import APIHealthMonitor
            from app.components.predictions_health import PredictionsHealthMonitor
            
            # Initialize monitors
            monitors = {
                'financial': FinancialHealthMonitor(),
                'platform': PlatformHealthMonitor(),
                'payment': PaymentHealthMonitor(),
                'api': APIHealthMonitor(),
                'predictions': PredictionsHealthMonitor()
            }
            
            # Check each component for alerts
            for component_name, monitor in monitors.items():
                try:
                    if hasattr(monitor, 'get_health_alerts'):
                        alerts = monitor.get_health_alerts()
                        
                        for alert in alerts:
                            self.add_alert(
                                component=alert.get('component', component_name),
                                metric=alert.get('metric', 'unknown'),
                                message=alert.get('message', 'Health check failed'),
                                severity=AlertSeverity(alert.get('severity', 'warning')),
                                value=alert.get('value'),
                                threshold=alert.get('threshold')
                            )
                            
                except Exception as e:
                    logger.error(f"Error checking {component_name} health: {e}")
            
        except Exception as e:
            logger.error(f"Error checking all health components: {e}")
    
    def _generate_alert_id(self, component: str, metric: str) -> str:
        """Generate unique alert ID"""
        return f"{component}_{metric}_{datetime.now().strftime('%Y%m%d')}"
    
    def _find_existing_alert(self, component: str, metric: str) -> Optional[Dict[str, Any]]:
        """Find existing alert by component and metric"""
        alert_id = self._generate_alert_id(component, metric)
        for alert in self.active_alerts:
            if alert.get('id') == alert_id:
                return alert
        return None
    
    def _send_notification(self, alert: Dict[str, Any]):
        """Send notification for alert"""
        try:
            # Send Slack notification if configured
            if self.config.SLACK_WEBHOOK_URL:
                self._send_slack_notification(alert)
            
            # Send email notification if configured
            if self.config.NOTIFICATION_EMAIL:
                self._send_email_notification(alert)
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def _send_slack_notification(self, alert: Dict[str, Any]):
        """Send Slack notification"""
        try:
            # Map severity to colors and emojis
            severity_config = {
                'info': {'color': '#36a64f', 'emoji': 'ℹ️'},
                'warning': {'color': '#ff9500', 'emoji': '⚠️'},
                'critical': {'color': '#ff0000', 'emoji': '🚨'}
            }
            
            config = severity_config.get(alert['severity'], severity_config['warning'])
            
            payload = {
                'attachments': [{
                    'color': config['color'],
                    'title': f"{config['emoji']} Katikaa Health Alert - {alert['severity'].upper()}",
                    'text': alert['message'],
                    'fields': [
                        {
                            'title': 'Component',
                            'value': alert['component'],
                            'short': True
                        },
                        {
                            'title': 'Metric',
                            'value': alert['metric'],
                            'short': True
                        }
                    ],
                    'timestamp': alert['timestamp']
                }]
            }
            
            # Add value and threshold if available
            if alert.get('value') is not None:
                payload['attachments'][0]['fields'].append({
                    'title': 'Current Value',
                    'value': str(alert['value']),
                    'short': True
                })
            
            if alert.get('threshold') is not None:
                payload['attachments'][0]['fields'].append({
                    'title': 'Threshold',
                    'value': str(alert['threshold']),
                    'short': True
                })
            
            response = requests.post(
                self.config.SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent for alert: {alert['id']}")
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def _send_email_notification(self, alert: Dict[str, Any]):
        """Send email notification"""
        try:
            # In a real implementation, this would use AWS SES or another email service
            # For now, just log the email notification
            logger.info(f"Email notification would be sent to {self.config.NOTIFICATION_EMAIL}")
            logger.info(f"Alert: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts"""
        try:
            summary = {
                'total_alerts': len(self.active_alerts),
                'critical_count': len([a for a in self.active_alerts if a.get('severity') == 'critical']),
                'warning_count': len([a for a in self.active_alerts if a.get('severity') == 'warning']),
                'info_count': len([a for a in self.active_alerts if a.get('severity') == 'info']),
                'unacknowledged_count': len([a for a in self.active_alerts if not a.get('acknowledged', False)]),
                'components_with_alerts': list(set([a.get('component') for a in self.active_alerts]))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def get_alerts_by_component(self, component: str) -> List[Dict[str, Any]]:
        """Get alerts for specific component"""
        try:
            return [
                alert for alert in self.active_alerts 
                if alert.get('component') == component
            ]
        except Exception as e:
            logger.error(f"Error getting alerts for component {component}: {e}")
            return []
    
    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            initial_count = len(self.active_alerts)
            self.active_alerts = [
                alert for alert in self.active_alerts
                if datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            cleared_count = initial_count - len(self.active_alerts)
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} old alerts")
            
        except Exception as e:
            logger.error(f"Error clearing old alerts: {e}")
    
    def export_alerts(self, format: str = 'json') -> str:
        """Export alerts in specified format"""
        try:
            if format.lower() == 'json':
                return json.dumps(self.active_alerts, indent=2)
            elif format.lower() == 'csv':
                # Convert to CSV format
                import csv
                import io
                
                output = io.StringIO()
                if self.active_alerts:
                    fieldnames = self.active_alerts[0].keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.active_alerts)
                
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting alerts: {e}")
            return ""
    
    def test_notification_system(self) -> bool:
        """Test notification system with a sample alert"""
        try:
            test_alert = {
                'id': 'test_alert',
                'component': 'system',
                'metric': 'test',
                'message': 'This is a test alert to verify notification system',
                'severity': 'info',
                'value': 'test_value',
                'threshold': 'test_threshold',
                'timestamp': datetime.now().isoformat(),
                'acknowledged': False
            }
            
            self._send_notification(test_alert)
            logger.info("Test notification sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error testing notification system: {e}")
            return False
