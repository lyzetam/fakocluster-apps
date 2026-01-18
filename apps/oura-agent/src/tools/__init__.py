"""Tool registry for Oura Health Agent.

All tools are registered here for use by the LangGraph agent.
"""

from src.tools.sleep import (
    get_last_night_sleep,
    get_sleep_quality,
    get_sleep_trends,
    get_sleep_stages_breakdown,
    get_sleep_efficiency_analysis,
    get_optimal_sleep_time,
)
from src.tools.activity import (
    get_today_activity,
    get_activity_trends,
    check_step_goal,
    get_activity_breakdown,
    get_calories_burned,
    get_met_minutes,
)
from src.tools.workouts import (
    get_recent_workouts,
    get_workout_summary,
    get_workout_by_type,
    get_workout_intensity_distribution,
)
from src.tools.readiness import (
    check_exercise_readiness,
    get_recovery_status,
    get_readiness_trends,
    get_readiness_contributors,
    get_temperature_deviation,
)
from src.tools.heart import (
    get_resting_heart_rate,
    get_hrv_analysis,
    get_heart_rate_during_sleep,
    get_hrv_balance,
)
from src.tools.stress import (
    get_stress_levels,
    get_stress_recovery_balance,
    get_resilience_status,
    get_resilience_trends,
)
from src.tools.advanced import (
    get_vo2_max,
    get_cardiovascular_age,
    get_spo2_levels,
    get_breathing_disturbance,
    get_respiratory_rate,
)
from src.tools.sessions import (
    get_meditation_sessions,
    get_breathing_sessions,
    get_session_hr_response,
)
from src.tools.trends import (
    get_weekly_health_summary,
    get_health_score_trends,
    compare_periods,
    get_day_of_week_patterns,
    get_correlations,
    get_best_and_worst_days,
)
from src.tools.recommendations import (
    get_sleep_recommendations,
    get_activity_recommendations,
    get_recovery_recommendations,
    get_personalized_insights,
)
from src.tools.memory_tools import (
    recall_past_insight,
    set_health_goal,
    get_active_goals,
    mark_goal_achieved,
    get_user_baselines,
    save_insight,
)
from src.tools.utils import (
    get_user_profile,
    get_ring_info,
    get_rest_mode_history,
    get_user_tags,
    get_data_collection_status,
)

# All tools available to the agent
ALL_TOOLS = [
    # Sleep (6)
    get_last_night_sleep,
    get_sleep_quality,
    get_sleep_trends,
    get_sleep_stages_breakdown,
    get_sleep_efficiency_analysis,
    get_optimal_sleep_time,
    # Activity (6)
    get_today_activity,
    get_activity_trends,
    check_step_goal,
    get_activity_breakdown,
    get_calories_burned,
    get_met_minutes,
    # Workouts (4)
    get_recent_workouts,
    get_workout_summary,
    get_workout_by_type,
    get_workout_intensity_distribution,
    # Readiness (5)
    check_exercise_readiness,
    get_recovery_status,
    get_readiness_trends,
    get_readiness_contributors,
    get_temperature_deviation,
    # Heart (4)
    get_resting_heart_rate,
    get_hrv_analysis,
    get_heart_rate_during_sleep,
    get_hrv_balance,
    # Stress (4)
    get_stress_levels,
    get_stress_recovery_balance,
    get_resilience_status,
    get_resilience_trends,
    # Advanced (5)
    get_vo2_max,
    get_cardiovascular_age,
    get_spo2_levels,
    get_breathing_disturbance,
    get_respiratory_rate,
    # Sessions (3)
    get_meditation_sessions,
    get_breathing_sessions,
    get_session_hr_response,
    # Trends (6)
    get_weekly_health_summary,
    get_health_score_trends,
    compare_periods,
    get_day_of_week_patterns,
    get_correlations,
    get_best_and_worst_days,
    # Recommendations (4)
    get_sleep_recommendations,
    get_activity_recommendations,
    get_recovery_recommendations,
    get_personalized_insights,
    # Memory (6)
    recall_past_insight,
    set_health_goal,
    get_active_goals,
    mark_goal_achieved,
    get_user_baselines,
    save_insight,
    # Utils (5)
    get_user_profile,
    get_ring_info,
    get_rest_mode_history,
    get_user_tags,
    get_data_collection_status,
]

__all__ = ["ALL_TOOLS"]
