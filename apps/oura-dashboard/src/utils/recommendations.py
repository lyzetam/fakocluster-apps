"""
Recommendations engine for Oura Health Dashboard
"""
import pandas as pd
from ui_config import METRIC_ICONS

class RecommendationEngine:
    """Generate personalized health recommendations based on Oura data"""
    
    @staticmethod
    def get_sleep_recommendations(df_sleep, sleep_trends=None):
        """Generate sleep-related recommendations"""
        recommendations = []
        
        # Filter for main sleep
        df_main = df_sleep[df_sleep['type'] == 'long_sleep']
        
        # Sleep duration
        avg_sleep = df_main['total_sleep_hours'].mean()
        if avg_sleep < 7:
            recommendations.append({
                'category': 'sleep_duration',
                'priority': 'high',
                'icon': '🛏️',
                'title': 'Increase sleep duration',
                'description': 'Aim for 7-9 hours of sleep per night. You\'re averaging {:.1f} hours.'.format(avg_sleep)
            })
        elif avg_sleep > 9:
            recommendations.append({
                'category': 'sleep_duration',
                'priority': 'medium',
                'icon': '⏰',
                'title': 'Monitor sleep duration',
                'description': 'You\'re sleeping more than 9 hours on average. This could indicate other health issues.'
            })
        
        # Sleep efficiency
        avg_efficiency = df_main['efficiency_percent'].mean()
        if avg_efficiency < 85:
            recommendations.append({
                'category': 'sleep_efficiency',
                'priority': 'high',
                'icon': '⚡',
                'title': 'Improve sleep efficiency',
                'description': 'Your sleep efficiency is {:.0f}%. Try maintaining consistent bedtime and wake time.'.format(avg_efficiency)
            })
        
        # Deep sleep
        avg_deep = df_main['deep_percentage'].mean()
        if avg_deep < 15:
            recommendations.append({
                'category': 'deep_sleep',
                'priority': 'medium',
                'icon': '💪',
                'title': 'Boost deep sleep',
                'description': 'Exercise regularly and keep bedroom cool (60-67°F) to increase deep sleep.'
            })
        
        # Sleep latency
        avg_latency = df_main['latency_minutes'].mean()
        if avg_latency > 20:
            recommendations.append({
                'category': 'sleep_latency',
                'priority': 'medium',
                'icon': '😴',
                'title': 'Reduce sleep latency',
                'description': 'Taking {:.0f} minutes to fall asleep. Develop a relaxing bedtime routine.'.format(avg_latency)
            })
        
        # HRV
        if 'hrv_avg' in df_main.columns:
            avg_hrv = df_main['hrv_avg'].mean()
            if pd.notna(avg_hrv) and avg_hrv < 30:
                recommendations.append({
                    'category': 'hrv',
                    'priority': 'high',
                    'icon': '🧘',
                    'title': 'Improve HRV',
                    'description': 'Practice stress management and breathing exercises to improve HRV.'
                })
        
        return recommendations
    
    @staticmethod
    def get_activity_recommendations(df_activity):
        """Generate activity-related recommendations"""
        recommendations = []
        
        # Steps
        avg_steps = df_activity['steps'].mean()
        days_above_10k = len(df_activity[df_activity['steps'] >= 10000])
        total_days = len(df_activity)
        
        if avg_steps < 7500:
            recommendations.append({
                'category': 'steps',
                'priority': 'high',
                'icon': '👟',
                'title': 'Increase daily steps',
                'description': 'Averaging {:.0f} steps/day. Aim for at least 7,500-10,000 steps.'.format(avg_steps)
            })
        
        if days_above_10k / total_days < 0.5:
            recommendations.append({
                'category': 'step_consistency',
                'priority': 'medium',
                'icon': '📊',
                'title': 'Improve step consistency',
                'description': 'Only {:.0%} of days above 10k steps. Try to be more consistent.'.format(days_above_10k / total_days)
            })
        
        # Active minutes
        avg_active = df_activity['total_active_minutes'].mean()
        if avg_active < 30:
            recommendations.append({
                'category': 'active_time',
                'priority': 'high',
                'icon': '🏃',
                'title': 'Increase active time',
                'description': 'Only {:.0f} active minutes/day. WHO recommends at least 30 minutes.'.format(avg_active)
            })
        
        # Sedentary time
        sedentary_pct = (df_activity['sedentary_minutes'].mean() / (24 * 60)) * 100
        if sedentary_pct > 60:
            recommendations.append({
                'category': 'sedentary',
                'priority': 'medium',
                'icon': '🪑',
                'title': 'Reduce sedentary time',
                'description': 'Sedentary {:.0f}% of the day. Take regular breaks to move.'.format(sedentary_pct)
            })
        
        # Inactivity alerts
        if 'inactivity_alerts' in df_activity.columns:
            avg_alerts = df_activity['inactivity_alerts'].mean()
            if avg_alerts > 5:
                recommendations.append({
                    'category': 'inactivity',
                    'priority': 'low',
                    'icon': '⏰',
                    'title': 'Reduce inactivity alerts',
                    'description': 'Getting {:.1f} inactivity alerts/day. Set reminders to move every hour.'.format(avg_alerts)
                })
        
        return recommendations
    
    @staticmethod
    def get_readiness_recommendations(df_readiness, df_stress=None):
        """Generate readiness and recovery recommendations"""
        recommendations = []
        
        # Readiness score
        avg_readiness = df_readiness['readiness_score'].mean()
        if avg_readiness < 70:
            recommendations.append({
                'category': 'readiness',
                'priority': 'high',
                'icon': '🔋',
                'title': 'Improve recovery',
                'description': 'Low readiness score ({:.0f}). Focus on sleep and stress management.'.format(avg_readiness)
            })
        
        # HRV Balance
        if 'hrv_balance' in df_readiness.columns:
            avg_hrv_balance = df_readiness['hrv_balance'].mean()
            if pd.notna(avg_hrv_balance) and avg_hrv_balance < -5:
                recommendations.append({
                    'category': 'hrv_balance',
                    'priority': 'high',
                    'icon': '💓',
                    'title': 'Restore HRV balance',
                    'description': 'HRV is below baseline. Consider reducing training intensity.'
                })
        
        # Resting heart rate
        if 'resting_heart_rate' in df_readiness.columns:
            avg_rhr = df_readiness['resting_heart_rate'].mean()
            rhr_trend = df_readiness['resting_heart_rate'].tail(7).mean() - df_readiness['resting_heart_rate'].head(7).mean()
            
            if rhr_trend > 3:
                recommendations.append({
                    'category': 'rhr',
                    'priority': 'medium',
                    'icon': '❤️',
                    'title': 'Monitor heart rate',
                    'description': 'Resting heart rate is trending up. This may indicate stress or overtraining.'
                })
        
        # Temperature deviation
        if 'temperature_deviation' in df_readiness.columns:
            recent_temp_dev = df_readiness['temperature_deviation'].tail(3).mean()
            if abs(recent_temp_dev) > 0.5:
                recommendations.append({
                    'category': 'temperature',
                    'priority': 'medium',
                    'icon': '🌡️',
                    'title': 'Monitor body temperature',
                    'description': 'Temperature deviation detected. This could indicate illness or hormonal changes.'
                })
        
        # Stress management
        if df_stress is not None and not df_stress.empty:
            avg_stress_ratio = df_stress['stress_recovery_ratio'].mean()
            if avg_stress_ratio > 1.5:
                recommendations.append({
                    'category': 'stress',
                    'priority': 'high',
                    'icon': '🧘',
                    'title': 'Manage stress levels',
                    'description': 'High stress-to-recovery ratio ({:.1f}). Try meditation or breathing exercises.'.format(avg_stress_ratio)
                })
        
        return recommendations
    
    @staticmethod
    def get_workout_recommendations(df_workouts):
        """Generate workout-related recommendations"""
        recommendations = []
        
        if df_workouts.empty:
            recommendations.append({
                'category': 'workout_frequency',
                'priority': 'high',
                'icon': '🏋️',
                'title': 'Start tracking workouts',
                'description': 'No workouts recorded. Regular exercise is crucial for health.'
            })
            return recommendations
        
        # Workout frequency
        days_with_workouts = df_workouts['date'].nunique()
        date_range = (df_workouts['date'].max() - df_workouts['date'].min()).days + 1
        workout_frequency = days_with_workouts / date_range
        
        if workout_frequency < 0.43:  # Less than 3 days per week
            recommendations.append({
                'category': 'workout_frequency',
                'priority': 'high',
                'icon': '📅',
                'title': 'Increase workout frequency',
                'description': 'Working out {:.0f} days/week. Aim for at least 3-4 days.'.format(workout_frequency * 7)
            })
        
        # Workout variety
        unique_activities = df_workouts['activity'].nunique()
        if unique_activities < 3:
            recommendations.append({
                'category': 'workout_variety',
                'priority': 'low',
                'icon': '🎯',
                'title': 'Add workout variety',
                'description': 'Only doing {} types of activities. Mix cardio, strength, and flexibility.'.format(unique_activities)
            })
        
        # Workout duration
        avg_duration = df_workouts['duration_minutes'].mean()
        if avg_duration < 30:
            recommendations.append({
                'category': 'workout_duration',
                'priority': 'medium',
                'icon': '⏱️',
                'title': 'Increase workout duration',
                'description': 'Average workout is {:.0f} minutes. Aim for at least 30 minutes.'.format(avg_duration)
            })
        
        return recommendations
    
    @staticmethod
    def prioritize_recommendations(recommendations, max_recommendations=5):
        """Sort and limit recommendations by priority"""
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        
        sorted_recs = sorted(
            recommendations,
            key=lambda x: priority_order.get(x['priority'], 4)
        )
        
        return sorted_recs[:max_recommendations]
    
    @staticmethod
    def format_recommendation(rec):
        """Format recommendation for display"""
        priority_colors = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }
        
        priority_icon = priority_colors.get(rec['priority'], '⚪')
        
        return f"{rec['icon']} **{rec['title']}** {priority_icon}\n{rec['description']}"