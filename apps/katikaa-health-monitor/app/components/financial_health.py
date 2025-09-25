"""
Financial Health Monitoring Component
Based on balances_analytics.ipynb analysis
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.config import config
from data.database import DatabaseManager

logger = logging.getLogger(__name__)

class FinancialHealthMonitor:
    """Monitor financial health metrics for Katikaa platform"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.cache_duration = 300  # 5 minutes cache
        self._cached_data = {}
        self._last_refresh = None
    
    def get_health_score(self) -> float:
        """Get overall financial health score (0-100)"""
        try:
            data = self.get_comprehensive_data()
            if not data:
                return 0.0
            
            score = 100.0
            
            # Transaction failure rate impact
            if data.get('failed_rate', 0) > 10:
                score -= 30
            elif data.get('failed_rate', 0) > 5:
                score -= 15
            
            # User funds trend impact
            funds_trend = data.get('funds_trend', 0)
            if funds_trend < -0.1:  # Declining by more than 10%
                score -= 25
            elif funds_trend < 0:  # Any decline
                score -= 10
            
            # Commission health impact
            if data.get('commission_revenue', 0) == 0:
                score -= 20
            
            # Transaction volume impact
            volume_trend = data.get('volume_trend', 0)
            if volume_trend < -0.2:  # Significant volume drop
                score -= 15
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating financial health score: {e}")
            return 0.0
    
    def get_comprehensive_data(self) -> Dict[str, Any]:
        """Get comprehensive financial health data"""
        try:
            if self._is_cache_valid():
                return self._cached_data
            
            logger.info("Fetching comprehensive financial data...")
            
            data = {
                'total_user_funds': self._get_total_user_funds(),
                'daily_volume': self._get_daily_transaction_volume(),
                'failed_rate': self._get_transaction_failure_rate(),
                'commission_revenue': self._get_daily_commission_revenue(),
                'user_balance_distribution': self._get_user_balance_distribution(),
                'transaction_trends': self._get_transaction_trends(),
                'commission_trends': self._get_commission_trends(),
                'source_analysis': self._get_source_analysis(),
                'funds_trend': self._get_funds_trend(),
                'volume_trend': self._get_volume_trend(),
                'top_users_by_balance': self._get_top_users_by_balance(),
                'transaction_summary': self._get_transaction_summary()
            }
            
            self._cached_data = data
            self._last_refresh = datetime.now()
            
            logger.info("Financial data fetched successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive financial data: {e}")
            return {}
    
    def get_wallet_transaction_analysis(self) -> Dict[str, Any]:
        """
        Get detailed wallet transaction analysis
        Based on balances_analytics.ipynb methodology
        """
        try:
            # Get FCFA wallet transactions with user insights
            fcfa_data = self._analyze_fcfa_wallet_transactions()
            
            # Get commission analysis
            commission_data = self._analyze_site_commission()
            
            # Get transaction source analysis
            source_data = self._analyze_transaction_sources()
            
            return {
                'fcfa_analysis': fcfa_data,
                'commission_analysis': commission_data,
                'source_analysis': source_data,
                'health_indicators': self._calculate_financial_health_indicators()
            }
            
        except Exception as e:
            logger.error(f"Error in wallet transaction analysis: {e}")
            return {}
    
    def create_financial_charts(self) -> Dict[str, Any]:
        """Create financial health visualization charts"""
        try:
            data = self.get_comprehensive_data()
            if not data:
                return {}
            
            charts = {}
            
            # Transaction volume trend chart
            charts['volume_trend'] = self._create_volume_trend_chart(
                data['transaction_trends']
            )
            
            # User balance distribution chart
            charts['balance_distribution'] = self._create_balance_distribution_chart(
                data['user_balance_distribution']
            )
            
            # Commission revenue trend chart
            charts['commission_trend'] = self._create_commission_trend_chart(
                data['commission_trends']
            )
            
            # Transaction source breakdown chart
            charts['source_breakdown'] = self._create_source_breakdown_chart(
                data['source_analysis']
            )
            
            # Financial health summary chart
            charts['health_summary'] = self._create_financial_health_summary()
            
            return charts
            
        except Exception as e:
            logger.error(f"Error creating financial charts: {e}")
            return {}
    
    def refresh(self):
        """Refresh cached data"""
        self._cached_data.clear()
        self._last_refresh = None
        logger.info("Financial health monitor refreshed")
    
    # Private helper methods
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self._last_refresh or not self._cached_data:
            return False
        
        age = (datetime.now() - self._last_refresh).total_seconds()
        return age < self.cache_duration
    
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
            return float(result[0]['total_funds']) if result and result[0]['total_funds'] else 0.0
        except Exception as e:
            logger.error(f"Error getting total user funds: {e}")
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
            return float(result[0]['daily_volume']) if result and result[0]['daily_volume'] else 0.0
        except Exception as e:
            logger.error(f"Error getting daily transaction volume: {e}")
            return 0.0
    
    def _get_transaction_failure_rate(self) -> float:
        """Get transaction failure rate percentage"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_transactions
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            
            if result and result[0]['total_transactions'] > 0:
                failure_rate = (result[0]['failed_transactions'] / result[0]['total_transactions']) * 100
                return float(failure_rate)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting transaction failure rate: {e}")
            return 0.0
    
    def _get_daily_commission_revenue(self) -> float:
        """Get daily commission revenue"""
        try:
            query = """
            SELECT SUM(commission_amount) as daily_commission
            FROM site_commission_view_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            result = self.db_manager.execute_query(query)
            return float(result[0]['daily_commission']) if result and result[0]['daily_commission'] else 0.0
        except Exception as e:
            logger.error(f"Error getting daily commission revenue: {e}")
            return 0.0
    
    def _get_user_balance_distribution(self) -> Dict[str, Any]:
        """Get user balance distribution data"""
        try:
            query = """
            SELECT 
                user_id,
                SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END) as net_balance
            FROM prediction_db_wallet_data_df
            WHERE currency_type = 'FCFA' AND status = 'SUCCESS'
            GROUP BY user_id
            HAVING net_balance > 0
            ORDER BY net_balance DESC
            LIMIT 100
            """
            result = self.db_manager.execute_query(query)
            
            if result:
                balances = [float(row['net_balance']) for row in result]
                return {
                    'balances': balances,
                    'total_users_with_funds': len(balances),
                    'avg_balance': sum(balances) / len(balances) if balances else 0,
                    'median_balance': sorted(balances)[len(balances)//2] if balances else 0,
                    'top_10_percent_total': sum(balances[:len(balances)//10]) if balances else 0
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting user balance distribution: {e}")
            return {}
    
    def _get_transaction_trends(self) -> List[Dict[str, Any]]:
        """Get transaction trends over the last 30 days"""
        try:
            query = """
            SELECT 
                DATE(created_at) as transaction_date,
                SUM(amount) as total_volume,
                COUNT(*) as transaction_count,
                COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_count,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY transaction_date
            """
            result = self.db_manager.execute_query(query)
            
            trends = []
            for row in result:
                trends.append({
                    'date': row['transaction_date'].strftime('%Y-%m-%d'),
                    'total_volume': float(row['total_volume']) if row['total_volume'] else 0,
                    'transaction_count': int(row['transaction_count']),
                    'successful_count': int(row['successful_count']),
                    'failed_count': int(row['failed_count']),
                    'success_rate': (int(row['successful_count']) / int(row['transaction_count']) * 100) 
                                  if int(row['transaction_count']) > 0 else 0
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting transaction trends: {e}")
            return []
    
    def _get_commission_trends(self) -> List[Dict[str, Any]]:
        """Get commission trends over the last 30 days"""
        try:
            query = """
            SELECT 
                DATE(created_at) as commission_date,
                SUM(commission_amount) as daily_commission,
                COUNT(*) as commission_count,
                currency_type
            FROM site_commission_view_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at), currency_type
            ORDER BY commission_date
            """
            result = self.db_manager.execute_query(query)
            
            trends = []
            for row in result:
                trends.append({
                    'date': row['commission_date'].strftime('%Y-%m-%d'),
                    'amount': float(row['daily_commission']),
                    'count': int(row['commission_count']),
                    'currency': row['currency_type']
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting commission trends: {e}")
            return []
    
    def _get_source_analysis(self) -> Dict[str, Any]:
        """Get transaction source analysis"""
        try:
            query = """
            SELECT 
                source,
                type,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount
            FROM prediction_db_wallet_data_df
            WHERE status = 'SUCCESS'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY source, type
            ORDER BY total_amount DESC
            """
            result = self.db_manager.execute_query(query)
            
            source_data = {}
            for row in result:
                source = row['source']
                if source not in source_data:
                    source_data[source] = {'CREDIT': {}, 'DEBIT': {}}
                
                source_data[source][row['type']] = {
                    'count': int(row['transaction_count']),
                    'total': float(row['total_amount']),
                    'average': float(row['avg_amount'])
                }
            
            return source_data
            
        except Exception as e:
            logger.error(f"Error getting source analysis: {e}")
            return {}
    
    def _get_funds_trend(self) -> float:
        """Get funds trend (percentage change over last 7 days)"""
        try:
            query = """
            SELECT 
                SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END) as net_change
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND currency_type = 'FCFA'
            AND status = 'SUCCESS'
            """
            result = self.db_manager.execute_query(query)
            
            if result and result[0]['net_change']:
                net_change = float(result[0]['net_change'])
                # Normalize to percentage (simplified calculation)
                total_funds = self._get_total_user_funds()
                return (net_change / total_funds) if total_funds > 0 else 0
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting funds trend: {e}")
            return 0.0
    
    def _get_volume_trend(self) -> float:
        """Get transaction volume trend (percentage change)"""
        try:
            # Get today's volume
            today_query = """
            SELECT SUM(amount) as volume
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND status = 'SUCCESS'
            """
            today_result = self.db_manager.execute_query(today_query)
            today_volume = float(today_result[0]['volume']) if today_result and today_result[0]['volume'] else 0
            
            # Get yesterday's volume
            yesterday_query = """
            SELECT SUM(amount) as volume
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 48 HOUR)
            AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND status = 'SUCCESS'
            """
            yesterday_result = self.db_manager.execute_query(yesterday_query)
            yesterday_volume = float(yesterday_result[0]['volume']) if yesterday_result and yesterday_result[0]['volume'] else 1
            
            return (today_volume - yesterday_volume) / yesterday_volume if yesterday_volume > 0 else 0
            
        except Exception as e:
            logger.error(f"Error getting volume trend: {e}")
            return 0.0
    
    def _get_top_users_by_balance(self) -> List[Dict[str, Any]]:
        """Get top users by balance"""
        try:
            query = """
            SELECT 
                w.user_id,
                u.user_name,
                u.email_id,
                SUM(CASE WHEN w.type = 'CREDIT' THEN w.amount ELSE -w.amount END) as net_balance
            FROM prediction_db_wallet_data_df w
            JOIN prediction_db_user_data_df u ON w.user_id = u.user_id
            WHERE w.currency_type = 'FCFA' AND w.status = 'SUCCESS'
            GROUP BY w.user_id, u.user_name, u.email_id
            HAVING net_balance > 0
            ORDER BY net_balance DESC
            LIMIT 20
            """
            result = self.db_manager.execute_query(query)
            
            top_users = []
            for row in result:
                top_users.append({
                    'user_id': int(row['user_id']),
                    'user_name': row['user_name'],
                    'email': row['email_id'],
                    'balance': float(row['net_balance'])
                })
            
            return top_users
            
        except Exception as e:
            logger.error(f"Error getting top users by balance: {e}")
            return []
    
    def _get_transaction_summary(self) -> Dict[str, Any]:
        """Get transaction summary for today"""
        try:
            query = """
            SELECT 
                type,
                COUNT(*) as count,
                SUM(amount) as total,
                AVG(amount) as average
            FROM prediction_db_wallet_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND currency_type = 'FCFA'
            AND status = 'SUCCESS'
            GROUP BY type
            """
            result = self.db_manager.execute_query(query)
            
            summary = {'CREDIT': {}, 'DEBIT': {}}
            for row in result:
                summary[row['type']] = {
                    'count': int(row['count']),
                    'total': float(row['total']),
                    'average': float(row['average'])
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {}
    
    # Analysis methods based on balances_analytics.ipynb
    def _analyze_fcfa_wallet_transactions(self) -> Dict[str, Any]:
        """Analyze FCFA wallet transactions with user insights"""
        try:
            # This implements the logic from balances_analytics.ipynb
            query = """
            SELECT 
                user_id,
                type,
                source,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count
            FROM prediction_db_wallet_data_df
            WHERE currency_type = 'FCFA' 
            AND status = 'SUCCESS'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY user_id, type, source
            """
            result = self.db_manager.execute_query(query)
            
            # Process results similar to the notebook logic
            user_analysis = {}
            for row in result:
                user_id = row['user_id']
                if user_id not in user_analysis:
                    user_analysis[user_id] = {'CREDIT': {}, 'DEBIT': {}, 'total_credits': 0, 'total_debits': 0}
                
                tx_type = row['type']
                source = row['source']
                amount = float(row['total_amount'])
                count = int(row['transaction_count'])
                
                user_analysis[user_id][tx_type][source] = {
                    'amount': amount,
                    'count': count
                }
                
                if tx_type == 'CREDIT':
                    user_analysis[user_id]['total_credits'] += amount
                else:
                    user_analysis[user_id]['total_debits'] += amount
            
            # Calculate net balances
            for user_id in user_analysis:
                user_analysis[user_id]['net_balance'] = (
                    user_analysis[user_id]['total_credits'] - 
                    user_analysis[user_id]['total_debits']
                )
            
            return user_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing FCFA wallet transactions: {e}")
            return {}
    
    def _analyze_site_commission(self) -> Dict[str, Any]:
        """Analyze site commission data"""
        try:
            query = """
            SELECT 
                currency_type,
                source,
                SUM(commission_amount) as total_commission,
                COUNT(*) as commission_count,
                AVG(commission_amount) as avg_commission
            FROM site_commission_view_data_df
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY currency_type, source
            ORDER BY total_commission DESC
            """
            result = self.db_manager.execute_query(query)
            
            analysis = {}
            for row in result:
                currency = row['currency_type']
                if currency not in analysis:
                    analysis[currency] = {}
                
                analysis[currency][row['source']] = {
                    'total': float(row['total_commission']),
                    'count': int(row['commission_count']),
                    'average': float(row['avg_commission'])
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing site commission: {e}")
            return {}
    
    def _analyze_transaction_sources(self) -> Dict[str, Any]:
        """Analyze transaction sources breakdown"""
        try:
            # Map sources to categories based on balances_analytics.ipynb
            source_mapping = {
                'MOBILE_MONEY': 'Mobile Money',
                'BONUS_ADMIN_TRANSFER': 'Bonus/Rewards',
                'WINNING_ADMIN_TRANSFER': 'Bonus/Rewards',
                'COMM_WINNER_PAYMENT': 'Winnings',
                'P2P_WINNER_PAYMENT': 'Winnings',
                'P2P_BET_REFUND': 'Refunds',
                'P2P_REFUND_MATCH_OFF': 'Refunds',
                'P2P_REFUND_NO_OPPONENT_FOUND': 'Refunds',
                'COMM_PAYMENT': 'Spending',
                'P2P_BET_CREATED': 'Spending',
                'P2P_BET_PAYMENT': 'Spending',
                'TRANSFER': 'Transfers'
            }
            
            query = """
            SELECT 
                source,
                type,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count
            FROM prediction_db_wallet_data_df
            WHERE currency_type = 'FCFA'
            AND status = 'SUCCESS'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY source, type
            """
            result = self.db_manager.execute_query(query)
            
            categorized_data = {}
            for row in result:
                source = row['source']
                category = source_mapping.get(source, 'Other')
                tx_type = row['type']
                
                if category not in categorized_data:
                    categorized_data[category] = {'CREDIT': 0, 'DEBIT': 0, 'count': 0}
                
                categorized_data[category][tx_type] += float(row['total_amount'])
                categorized_data[category]['count'] += int(row['transaction_count'])
            
            return categorized_data
            
        except Exception as e:
            logger.error(f"Error analyzing transaction sources: {e}")
            return {}
    
    def _calculate_financial_health_indicators(self) -> Dict[str, Any]:
        """Calculate financial health indicators"""
        try:
            indicators = {}
            
            # Get current metrics
            data = self.get_comprehensive_data()
            
            # Calculate health indicators
            indicators['liquidity_ratio'] = self._calculate_liquidity_ratio(data)
            indicators['transaction_velocity'] = self._calculate_transaction_velocity(data)
            indicators['user_engagement_financial'] = self._calculate_user_financial_engagement(data)
            indicators['revenue_stability'] = self._calculate_revenue_stability(data)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating financial health indicators: {e}")
            return {}
    
    def _calculate_liquidity_ratio(self, data: Dict[str, Any]) -> float:
        """Calculate platform liquidity ratio"""
        try:
            total_funds = data.get('total_user_funds', 0)
            daily_volume = data.get('daily_volume', 0)
            
            if daily_volume > 0:
                return total_funds / daily_volume
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_transaction_velocity(self, data: Dict[str, Any]) -> float:
        """Calculate transaction velocity (transactions per day)"""
        try:
            trends = data.get('transaction_trends', [])
            if trends:
                recent_days = trends[-7:]  # Last 7 days
                avg_daily_transactions = sum(day['transaction_count'] for day in recent_days) / len(recent_days)
                return avg_daily_transactions
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_user_financial_engagement(self, data: Dict[str, Any]) -> float:
        """Calculate user financial engagement score"""
        try:
            # Simplified calculation based on active users with transactions
            summary = data.get('transaction_summary', {})
            credit_count = summary.get('CREDIT', {}).get('count', 0)
            debit_count = summary.get('DEBIT', {}).get('count', 0)
            
            # Assume total active users (would be calculated from user engagement component)
            total_active_users = 1000  # Placeholder
            
            if total_active_users > 0:
                financial_users = len(set([credit_count, debit_count]))
                return (financial_users / total_active_users) * 100
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_revenue_stability(self, data: Dict[str, Any]) -> float:
        """Calculate revenue stability indicator"""
        try:
            commission_trends = data.get('commission_trends', [])
            if len(commission_trends) < 7:
                return 0.0
            
            # Calculate coefficient of variation for revenue stability
            recent_revenues = [day['amount'] for day in commission_trends[-7:]]
            if not recent_revenues:
                return 0.0
            
            mean_revenue = sum(recent_revenues) / len(recent_revenues)
            if mean_revenue == 0:
                return 0.0
            
            variance = sum((x - mean_revenue) ** 2 for x in recent_revenues) / len(recent_revenues)
            std_dev = variance ** 0.5
            
            # Stability score (100 - coefficient of variation)
            cv = (std_dev / mean_revenue) * 100
            return max(0, 100 - cv)
            
        except Exception:
            return 0.0
    
    # Chart creation methods
    def _create_volume_trend_chart(self, trends: List[Dict[str, Any]]) -> go.Figure:
        """Create transaction volume trend chart"""
        try:
            if not trends:
                return go.Figure()
            
            dates = [trend['date'] for trend in trends]
            volumes = [trend['total_volume'] for trend in trends]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=volumes,
                mode='lines+markers',
                name='Transaction Volume',
                line=dict(color='#1f77b4', width=2)
            ))
            
            fig.update_layout(
                title='Transaction Volume Trend (Last 30 Days)',
                xaxis_title='Date',
                yaxis_title='Volume (FCFA)',
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating volume trend chart: {e}")
            return go.Figure()
    
    def _create_balance_distribution_chart(self, distribution: Dict[str, Any]) -> go.Figure:
        """Create user balance distribution chart"""
        try:
            if not distribution or not distribution.get('balances'):
                return go.Figure()
            
            balances = distribution['balances']
            
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=balances,
                nbinsx=20,
                name='User Balance Distribution',
                marker_color='#2ca02c'
            ))
            
            fig.update_layout(
                title='User Balance Distribution',
                xaxis_title='Balance (FCFA)',
                yaxis_title='Number of Users',
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating balance distribution chart: {e}")
            return go.Figure()
    
    def _create_commission_trend_chart(self, trends: List[Dict[str, Any]]) -> go.Figure:
        """Create commission revenue trend chart"""
        try:
            if not trends:
                return go.Figure()
            
            # Group by date and currency
            eth_data = [t for t in trends if t['currency'] == 'ETH']
            fcfa_data = [t for t in trends if t['currency'] == 'FCFA']
            
            fig = go.Figure()
            
            if eth_data:
                fig.add_trace(go.Scatter(
                    x=[d['date'] for d in eth_data],
                    y=[d['amount'] for d in eth_data],
                    mode='lines+markers',
                    name='ETH Commission',
                    line=dict(color='#ff7f0e')
                ))
            
            if fcfa_data:
                fig.add_trace(go.Scatter(
                    x=[d['date'] for d in fcfa_data],
                    y=[d['amount'] for d in fcfa_data],
                    mode='lines+markers',
                    name='FCFA Commission',
                    line=dict(color='#2ca02c')
                ))
            
            fig.update_layout(
                title='Commission Revenue Trend',
                xaxis_title='Date',
                yaxis_title='Commission Amount',
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating commission trend chart: {e}")
            return go.Figure()
    
    def _create_source_breakdown_chart(self, source_data: Dict[str, Any]) -> go.Figure:
        """Create transaction source breakdown chart"""
        try:
            if not source_data:
                return go.Figure()
            
            # Prepare data for pie chart
            sources = []
            values = []
            
            for source, data in source_data.items():
                total_amount = 0
                for tx_type in ['CREDIT', 'DEBIT']:
                    if tx_type in data:
                        total_amount += data[tx_type].get('total', 0)
                
                if total_amount > 0:
                    sources.append(source)
                    values.append(total_amount)
            
            if not sources:
                return go.Figure()
            
            fig = go.Figure()
            fig.add_trace(go.Pie(
                labels=sources,
                values=values,
                name='Transaction Sources'
            ))
            
            fig.update_layout(
                title='Transaction Source Breakdown (Last 7 Days)',
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating source breakdown chart: {e}")
            return go.Figure()
    
    def _create_financial_health_summary(self) -> go.Figure:
        """Create financial health summary chart"""
        try:
            data = self.get_comprehensive_data()
            if not data:
                return go.Figure()
            
            # Create indicators chart
            indicators = [
                'Total User Funds',
                'Daily Volume',
                'Commission Revenue',
                'Failed Rate'
            ]
            
            values = [
                data.get('total_user_funds', 0),
                data.get('daily_volume', 0), 
                data.get('commission_revenue', 0),
                data.get('failed_rate', 0)
            ]
            
            # Normalize values for display (different scales)
            normalized_values = []
            for i, value in enumerate(values):
                if i == 3:  # Failed rate is percentage
                    normalized_values.append(value)
                else:  # Financial amounts
                    normalized_values.append(value / 1000)  # Convert to thousands
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=indicators,
                y=normalized_values,
                name='Financial Metrics',
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            ))
            
            fig.update_layout(
                title='Financial Health Summary',
                xaxis_title='Metrics',
                yaxis_title='Values',
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating financial health summary: {e}")
            return go.Figure()
