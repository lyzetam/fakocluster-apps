"""
Core health metrics calculation for Katikaa platform monitoring
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.config import config
from data.database import DatabaseManager

logger = logging.getLogger(__name__)

class HealthMetrics:
    """Core health metrics calculation and aggregation"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.last_refresh = None
        self._cached_metrics = {}
        
    def calculate_overall_health(self) -> float:
        """Calculate overall platform health score (0-100)"""
        try:
            # Get individual component health scores
            financial_score = self._get_financial_health_score()
            platform_score = self._get_platform_health_score()
            payment_score = self._get_payment_health_score()
            api_score = self._get_api_health_score()
            predictions_score = self._get_predictions_health_score()
            
            # Weighted average (adjust weights based on business priorities)
            weights = {
                'financial': 0.3,
                'platform': 0.25,
                'payment': 0.2,
                'api': 0.15,
                'predictions': 0.1
            }
            
            overall_score = (
                financial_score * weights['financial'] +
                platform_score * weights['platform'] +
                payment_score * weights['payment'] +
                api_score * weights['api'] +
                predictions_score * weights['predictions']
            )
            
            return min(max(overall_score, 0), 100)  # Ensure 0-100 range
            
        except Exception as e:
            logger.error(f"Error calculating overall health: {e}")
            return 0.0
    
    def get_key_metrics(self) -> Dict[str, Any]:
        """Get key metrics for overview dashboard"""
        try:
            return {
                'financial': self._get_financial_key_metrics(),
                'engagement': self._get_engagement_key_metrics(),
                'performance': self._get_performance_key_metrics(),
                'alerts': self._get_alerts_summary()
            }
        except Exception as e:
            logger.error(f"Error getting key metrics: {e}")
            return {}
    
    def get_health_trends(self) -> Dict[str, Any]:
        """Get health trends over time for dashboard"""
        try:
            # Get last 30 days of health data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            return {
                'dates': self._get_date_range(start_date, end_date),
                'overall_health': self._get_health_trend_data('overall', start_date, end_date),
                'financial_health': self._get_health_trend_data('financial', start_date, end_date),
                'platform_health': self._get_health_trend_data('platform', start_date, end_date),
                'payment_health': self._get_health_trend_data('payment', start_date, end_date)
            }
        except Exception as e:
            logger.error(f"Error getting health trends: {e}")
            return {}
    
    def refresh(self):
        """Refresh cached metrics"""
        try:
            logger.info("Refreshing health metrics...")
            self._cached_metrics.clear()
            self.last_refresh = datetime.now()
            
            # Pre-calculate frequently used metrics
            self._cached_metrics['overall_health'] = self.calculate_overall_health()
            self._cached_metrics['key_metrics'] = self.get_key_metrics()
            
            logger.info("Health metrics refreshed successfully")
            
        except Exception as e:
            logger.error(f"Error refreshing health metrics: {e}")
    
    def _get_financial_health_score(self) -> float:
        """Calculate financial health score (0-100)"""
        try:
            # Based on balances_analytics.ipynb logic
            score = 100.0
            
            # Check transaction failure rate
            failed_rate = self._get_transaction_failure_rate()
            if failed_rate > 10:  # More than 10% failure
                score -= 30
            elif failed_rate > 5:  # More than 5% failure
                score -= 15
            
            # Check user fund balance trends
            balance_trend = self._get_balance_trend()
            if balance_trend < -0.1:  # Decreasing by more than 10%
                score -= 20
            elif balance_trend < -0.05:  # Decreasing by more than 5%
                score -= 10
            
            # Check commission revenue
            commission_health = self._get_commission_health()
            if not commission_health:
                score -= 25
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating financial health score: {e}")
            return 0.0
    
    def _get_platform_health_score(self) -> float:
        """Calculate platform health score (0-100)"""
        try:
            # Based on katikaa_analytics.ipynb logic
            score = 100.0
            
            # Check daily active user trends
            dau_trend = self._get_dau_trend()
            if dau_trend < -0.2:  # Decreasing by more than 20%
                score -= 30
            elif dau_trend < -0.1:  # Decreasing by more than 10%
                score -= 15
            
            # Check community activity
            community_activity = self._get_community_activity_score()
            if community_activity < 50:
                score -= 25
            
            # Check prediction engagement
            prediction_engagement = self._get_prediction_engagement_score()
            if prediction_engagement < 50:
                score -= 20
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating platform health score: {e}")
            return 0.0
    
    def _get_payment_health_score(self) -> float:
        """Calculate payment gateway health score (0-100)"""
        try:
            # Based on Fapshi_Workbook.ipynb logic
            score = 100.0
            
            # Check Fapshi success rate
            success_rate = self._get_payment_success_rate()
            if success_rate < 80:  # Less than 80% success
                score -= 40
            elif success_rate < 90:  # Less than 90% success
                score -= 20
            
            # Check balance sufficiency
            balance_status = self._check_payment_balance_status()
            if not balance_status:
                score -= 30
            
            # Check transaction volume trends
            volume_trend = self._get_payment_volume_trend()
            if volume_trend < -0.3:  # Significant volume drop
                score -= 15
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating payment health score: {e}")
            return 0.0
    
    def _get_api_health_score(self) -> float:
        """Calculate API health score (0-100)"""
        try:
            # Based on sportmonks usage.ipynb logic
            score = 100.0
            
            # Check API usage against quotas
            usage_percent = self._get_api_usage_percentage()
            if usage_percent > 90:  # Over 90% of quota
                score -= 30
            elif usage_percent > 80:  # Over 80% of quota
                score -= 15
            
            # Check API error rates
            error_rate = self._get_api_error_rate()
            if error_rate > 10:  # More than 10% errors
                score -= 25
            elif error_rate > 5:  # More than 5% errors
                score -= 10
            
            # Check response times
            avg_response_time = self._get_average_response_time()
            if avg_response_time > 5000:  # More than 5 seconds
                score -= 20
            elif avg_response_time > 2000:  # More than 2 seconds
                score -= 10
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating API health score: {e}")
            return 0.0
    
    def _get_predictions_health_score(self) -> float:
        """Calculate predictions health score (0-100)"""
        try:
            # Based on predictions_analytics notebooks logic
            score = 100.0
            
            # Check prediction volume trends
            volume_trend = self._get_predictions_volume_trend()
            if volume_trend < -0.2:  # Significant drop
                score -= 25
            
            # Check prediction accuracy
            accuracy = self._get_prediction_accuracy()
            if accuracy < 40:  # Very low accuracy
                score -= 20
            elif accuracy < 50:  # Low accuracy
                score -= 10
            
            # Check user engagement with predictions
            engagement = self._get_prediction_user_engagement()
            if engagement < 30:  # Low engagement
                score -= 15
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating predictions health score: {e}")
            return 0.0
    
    # Helper methods for specific calculations
    def _get_transaction_failure_rate(self) -> float:
        """Get transaction failure rate percentage"""
        try:
            query = """
            SELECT 
                (COUNT(CASE WHEN status = 'FAILED' THEN 1 END) * 100.0 / COUNT(*)) as failure_rate
            FROM prediction_db_wallet_data_df 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['failure_rate'] if result else 0.0
        except Exception:
            return 0.0
    
    def _get_balance_trend(self) -> float:
        """Get user balance trend (positive/negative percentage change)"""
        try:
            query = """
            SELECT 
                (SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END)) as net_change
            FROM prediction_db_wallet_data_df 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
            AND currency_type = 'FCFA'
            """
            result = self.db_manager.execute_query(query)
            net_change = result[0]['net_change'] if result else 0
            
            # Calculate percentage change (simplified)
            return net_change / 1000000 if net_change else 0  # Normalize
        except Exception:
            return 0.0
    
    def _get_commission_health(self) -> bool:
        """Check if commission generation is healthy"""
        try:
            query = """
            SELECT COUNT(*) as commission_count
            FROM site_commission_view_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['commission_count'] > 0 if result else False
        except Exception:
            return False
    
    def _get_dau_trend(self) -> float:
        """Get Daily Active Users trend"""
        try:
            # Simplified DAU calculation
            query = """
            SELECT COUNT(DISTINCT user_id) as dau
            FROM prediction_db_user_data_df
            WHERE last_login >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            today_dau = result[0]['dau'] if result else 0
            
            # Compare with yesterday (simplified)
            query_yesterday = """
            SELECT COUNT(DISTINCT user_id) as dau
            FROM prediction_db_user_data_df
            WHERE last_login >= DATE_SUB(NOW(), INTERVAL 48 HOUR)
            AND last_login < DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result_yesterday = self.db_manager.execute_query(query_yesterday)
            yesterday_dau = result_yesterday[0]['dau'] if result_yesterday else 1
            
            return (today_dau - yesterday_dau) / yesterday_dau if yesterday_dau > 0 else 0
        except Exception:
            return 0.0
    
    def _get_community_activity_score(self) -> float:
        """Get community activity score (0-100)"""
        try:
            query = """
            SELECT COUNT(*) as active_communities
            FROM prediction_db_community_data_df c
            WHERE EXISTS (
                SELECT 1 FROM prediction_db_prediction_data_df p
                WHERE p.community_id = c.community_id
                AND p.creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            )
            """
            result = self.db_manager.execute_query(query)
            active_communities = result[0]['active_communities'] if result else 0
            
            # Normalize to 0-100 scale (assuming 50+ active communities is good)
            return min(active_communities * 2, 100)
        except Exception:
            return 0.0
    
    def _get_prediction_engagement_score(self) -> float:
        """Get prediction engagement score (0-100)"""
        try:
            query = """
            SELECT COUNT(*) as predictions_today
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            predictions_today = result[0]['predictions_today'] if result else 0
            
            # Normalize to 0-100 scale (assuming 100+ predictions per day is good)
            return min(predictions_today, 100)
        except Exception:
            return 0.0
    
    def _get_payment_success_rate(self) -> float:
        """Get Fapshi payment success rate"""
        # This would integrate with Fapshi API
        try:
            # Placeholder - would implement actual Fapshi API call
            return 95.0  # Assume 95% success rate for now
        except Exception:
            return 0.0
    
    def _check_payment_balance_status(self) -> bool:
        """Check if payment gateway balance is sufficient"""
        # This would integrate with Fapshi API
        try:
            # Placeholder - would implement actual balance check
            return True
        except Exception:
            return False
    
    def _get_payment_volume_trend(self) -> float:
        """Get payment volume trend"""
        # This would integrate with Fapshi API
        try:
            # Placeholder - would implement actual volume trend calculation
            return 0.05  # Assume 5% growth
        except Exception:
            return 0.0
    
    def _get_api_usage_percentage(self) -> float:
        """Get API usage as percentage of quota"""
        try:
            # This would integrate with SportMonks usage data
            # Placeholder - would implement actual usage calculation
            return 65.0  # Assume 65% of quota used
        except Exception:
            return 0.0
    
    def _get_api_error_rate(self) -> float:
        """Get API error rate percentage"""
        try:
            # Placeholder - would implement actual error rate calculation
            return 2.5  # Assume 2.5% error rate
        except Exception:
            return 0.0
    
    def _get_average_response_time(self) -> float:
        """Get average API response time in milliseconds"""
        try:
            # Placeholder - would implement actual response time calculation
            return 1200.0  # Assume 1.2 second average response
        except Exception:
            return 0.0
    
    def _get_predictions_volume_trend(self) -> float:
        """Get predictions volume trend"""
        try:
            # Compare today vs yesterday prediction counts
            query_today = """
            SELECT COUNT(*) as count
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result_today = self.db_manager.execute_query(query_today)
            today_count = result_today[0]['count'] if result_today else 0
            
            query_yesterday = """
            SELECT COUNT(*) as count
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 48 HOUR)
            AND creation_date < DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result_yesterday = self.db_manager.execute_query(query_yesterday)
            yesterday_count = result_yesterday[0]['count'] if result_yesterday else 1
            
            return (today_count - yesterday_count) / yesterday_count if yesterday_count > 0 else 0
        except Exception:
            return 0.0
    
    def _get_prediction_accuracy(self) -> float:
        """Get overall prediction accuracy percentage"""
        try:
            query = """
            SELECT AVG(total_points) as avg_accuracy
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 7 DAYS)
            AND total_points IS NOT NULL
            """
            result = self.db_manager.execute_query(query)
            return result[0]['avg_accuracy'] if result and result[0]['avg_accuracy'] else 50.0
        except Exception:
            return 50.0
    
    def _get_prediction_user_engagement(self) -> float:
        """Get prediction user engagement percentage"""
        try:
            query = """
            SELECT 
                (COUNT(DISTINCT user_id) * 100.0 / (
                    SELECT COUNT(*) FROM prediction_db_user_data_df
                )) as engagement_rate
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['engagement_rate'] if result else 0.0
        except Exception:
            return 0.0
    
    def _get_financial_key_metrics(self) -> Dict[str, Any]:
        """Get financial key metrics"""
        try:
            return {
                'total_user_funds': self._get_total_user_funds(),
                'daily_volume': self._get_daily_transaction_volume(),
                'commission_revenue': self._get_daily_commission(),
                'failed_transactions': self._get_failed_transaction_count()
            }
        except Exception:
            return {}
    
    def _get_engagement_key_metrics(self) -> Dict[str, Any]:
        """Get user engagement key metrics"""
        try:
            return {
                'dau': self._get_daily_active_users(),
                'mau': self._get_monthly_active_users(),
                'active_communities': self._get_active_communities_count(),
                'daily_predictions': self._get_daily_predictions_count()
            }
        except Exception:
            return {}
    
    def _get_performance_key_metrics(self) -> Dict[str, Any]:
        """Get performance key metrics"""
        try:
            return {
                'api_usage': self._get_api_usage_percentage(),
                'response_time': self._get_average_response_time(),
                'error_rate': self._get_api_error_rate(),
                'uptime': 99.9  # Placeholder
            }
        except Exception:
            return {}
    
    def _get_alerts_summary(self) -> Dict[str, Any]:
        """Get alerts summary"""
        try:
            return {
                'critical': 0,  # Placeholder
                'warning': 1,   # Placeholder
                'info': 2       # Placeholder
            }
        except Exception:
            return {}
    
    # Additional helper methods would be implemented here
    def _get_date_range(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Get list of dates between start and end"""
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        return dates
    
    def _get_health_trend_data(self, component: str, start_date: datetime, end_date: datetime) -> List[float]:
        """Get health trend data for a specific component"""
        # Placeholder - would implement actual trend calculation
        # Return sample data for now
        import random
        dates = self._get_date_range(start_date, end_date)
        return [random.uniform(60, 95) for _ in dates]
    
    # Database query helper methods
    def _get_total_user_funds(self) -> float:
        """Get total user funds in FCFA"""
        try:
            query = """
            SELECT SUM(
                CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END
            ) as total_funds
            FROM prediction_db_wallet_data_df
            WHERE currency_type = 'FCFA' AND status = 'SUCCESS'
            """
            result = self.db_manager.execute_query(query)
            return result[0]['total_funds'] if result and result[0]['total_funds'] else 0.0
        except Exception:
            return 0.0
    
    def _get_daily_transaction_volume(self) -> float:
        """Get daily transaction volume"""
        try:
            query = """
            SELECT SUM(amount) as daily_volume
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND status = 'SUCCESS'
            """
            result = self.db_manager.execute_query(query)
            return result[0]['daily_volume'] if result and result[0]['daily_volume'] else 0.0
        except Exception:
            return 0.0
    
    def _get_daily_commission(self) -> float:
        """Get daily commission revenue"""
        try:
            query = """
            SELECT SUM(commission_amount) as daily_commission
            FROM site_commission_view_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['daily_commission'] if result and result[0]['daily_commission'] else 0.0
        except Exception:
            return 0.0
    
    def _get_failed_transaction_count(self) -> int:
        """Get count of failed transactions today"""
        try:
            query = """
            SELECT COUNT(*) as failed_count
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND status = 'FAILED'
            """
            result = self.db_manager.execute_query(query)
            return result[0]['failed_count'] if result else 0
        except Exception:
            return 0
    
    def _get_daily_active_users(self) -> int:
        """Get daily active users count"""
        try:
            query = """
            SELECT COUNT(DISTINCT user_id) as dau
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['dau'] if result else 0
        except Exception:
            return 0
    
    def _get_monthly_active_users(self) -> int:
        """Get monthly active users count"""
        try:
            query = """
            SELECT COUNT(DISTINCT user_id) as mau
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['mau'] if result else 0
        except Exception:
            return 0
    
    def _get_active_communities_count(self) -> int:
        """Get active communities count"""
        try:
            query = """
            SELECT COUNT(DISTINCT community_id) as active_communities
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['active_communities'] if result else 0
        except Exception:
            return 0
    
    def _get_daily_predictions_count(self) -> int:
        """Get daily predictions count"""
        try:
            query = """
            SELECT COUNT(*) as daily_predictions
            FROM prediction_db_prediction_data_df
            WHERE creation_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return result[0]['daily_predictions'] if result else 0
        except Exception:
            return 0
