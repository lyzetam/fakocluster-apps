"""Activity analysis tools for Oura Health Agent.

These tools provide insights into daily activity, steps, and movement patterns.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_today_activity(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get today's activity summary including steps, calories, and activity score.

    Use this when the user asks about their activity today, how active they've been,
    or their current step count.

    Returns:
        Today's activity summary
    """
    data = await queries.get_today_activity(db_session)

    if not data:
        return "No activity data found for today yet. Keep wearing your ring!"

    return f"""Today's Activity Summary:

Activity Score: {data.get('score', 'N/A')}/100
Steps: {data.get('steps', 0):,}
Active Calories: {data.get('active_calories', 'N/A')} kcal
Total Calories: {data.get('total_burn', 'N/A')} kcal

Movement Breakdown:
- High Activity: {data.get('high_activity_time', 0)} min
- Medium Activity: {data.get('medium_activity_time', 0)} min
- Low Activity: {data.get('low_activity_time', 0)} min
- Sedentary Time: {data.get('sedentary_time', 0)} min
- Resting Time: {data.get('resting_time', 0)} min

Walking Distance: {data.get('equivalent_walking_distance', 'N/A')} meters
MET Minutes: {data.get('met_min_inactive', 0) + data.get('met_min_medium', 0) + data.get('met_min_high', 0)}

Goal Progress:
- Activity Goal: {data.get('target_calories', 'N/A')} kcal
- Progress: {data.get('cal_active', 0)}/{data.get('target_calories', 0)} kcal"""


@tool
async def get_activity_trends(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get activity trends over a period of time.

    Use this when the user asks about their activity patterns, weekly activity,
    or how active they've been recently.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Activity trend analysis
    """
    data = await queries.get_activity_trends(db_session, days)

    if not data or len(data) == 0:
        return f"No activity data found for the last {days} days."

    steps = [d.get('steps', 0) for d in data if d.get('steps') is not None]
    scores = [d.get('score', 0) for d in data if d.get('score')]
    calories = [d.get('active_calories', 0) for d in data if d.get('active_calories')]

    avg_steps = sum(steps) / len(steps) if steps else 0
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_calories = sum(calories) / len(calories) if calories else 0
    total_steps = sum(steps)

    trend_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('steps', 0):,} steps, Score {d.get('score', 'N/A')}"
        for d in data[:7]
    ])

    return f"""Activity Trends (Last {days} Days):

Average Daily Steps: {avg_steps:,.0f}
Total Steps: {total_steps:,}
Average Activity Score: {avg_score:.0f}/100
Average Active Calories: {avg_calories:.0f} kcal

Daily Breakdown:
{trend_data}

Step Goals:
- 10,000 steps/day: {'Meeting goal' if avg_steps >= 10000 else f'Need {10000 - avg_steps:.0f} more steps/day'}
- 7,500 steps/day: {'Meeting goal' if avg_steps >= 7500 else f'Need {7500 - avg_steps:.0f} more steps/day'}"""


@tool
async def check_step_goal(
    goal: Annotated[int, "Step goal to check against (default 10000)"] = 10000,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Check progress toward a daily step goal.

    Use this when the user asks if they hit their step goal, or about
    reaching a specific number of steps.

    Args:
        goal: Target step count (default 10,000)

    Returns:
        Step goal progress
    """
    data = await queries.get_today_activity(db_session)

    if not data:
        return "No activity data found for today."

    steps = data.get('steps', 0)
    remaining = max(0, goal - steps)
    percentage = (steps / goal * 100) if goal > 0 else 0

    if steps >= goal:
        return f"""Step Goal Achieved!

Current Steps: {steps:,}
Goal: {goal:,}
Progress: {percentage:.0f}%

You've exceeded your goal by {steps - goal:,} steps. Great job!"""
    else:
        return f"""Step Goal Progress:

Current Steps: {steps:,}
Goal: {goal:,}
Progress: {percentage:.0f}%
Remaining: {remaining:,} steps

Keep moving! You're {percentage:.0f}% of the way there."""


@tool
async def get_activity_breakdown(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get a breakdown of activity intensity levels for today.

    Use this when the user asks about their activity types, sedentary time,
    or movement patterns throughout the day.

    Returns:
        Activity intensity breakdown
    """
    data = await queries.get_today_activity(db_session)

    if not data:
        return "No activity data found for today."

    high = data.get('high_activity_time', 0)
    medium = data.get('medium_activity_time', 0)
    low = data.get('low_activity_time', 0)
    sedentary = data.get('sedentary_time', 0)
    resting = data.get('resting_time', 0)

    total_active = high + medium + low
    total_inactive = sedentary + resting

    return f"""Activity Intensity Breakdown (Today):

Active Time: {total_active} minutes
- High Intensity: {high} min (vigorous exercise)
- Medium Intensity: {medium} min (brisk walking, light exercise)
- Low Intensity: {low} min (gentle movement)

Inactive Time: {total_inactive} minutes
- Sedentary: {sedentary} min (sitting, light standing)
- Resting: {resting} min (sleep, lying down)

Recommendations:
- WHO recommends 150-300 min/week of moderate activity
- Weekly high intensity target: 75-150 min
- Your weekly moderate pace: ~{medium * 7} min (estimated)

Current Status:
- Sedentary: {'Consider taking breaks to move' if sedentary > 480 else 'Good movement throughout the day'}"""


@tool
async def get_calories_burned(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get calorie burn data over a period of time.

    Use this when the user asks about calories burned, energy expenditure,
    or caloric output.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Calorie burn analysis
    """
    data = await queries.get_calories_data(db_session, days)

    if not data or len(data) == 0:
        return f"No calorie data found for the last {days} days."

    active_cals = [d.get('active_calories', 0) for d in data if d.get('active_calories')]
    total_cals = [d.get('total_burn', 0) for d in data if d.get('total_burn')]

    avg_active = sum(active_cals) / len(active_cals) if active_cals else 0
    avg_total = sum(total_cals) / len(total_cals) if total_cals else 0
    total_burned = sum(total_cals)

    return f"""Calorie Burn Analysis (Last {days} Days):

Average Daily Total Burn: {avg_total:.0f} kcal
Average Daily Active Calories: {avg_active:.0f} kcal
Total Calories Burned: {total_burned:,.0f} kcal

Breakdown:
- Basal Metabolic Rate (estimated): {avg_total - avg_active:.0f} kcal/day
- Activity Calories: {avg_active:.0f} kcal/day

Your active calories represent {(avg_active/avg_total*100) if avg_total > 0 else 0:.0f}% of your total daily burn.

Note: For weight management, track these trends alongside nutrition."""


@tool
async def get_met_minutes(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get MET (Metabolic Equivalent of Task) minutes data over time.

    Use this when the user asks about MET minutes, exercise intensity,
    or workout effort quantification.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        MET minutes analysis
    """
    data = await queries.get_met_data(db_session, days)

    if not data or len(data) == 0:
        return f"No MET data found for the last {days} days."

    total_met = sum([
        d.get('met_min_inactive', 0) + d.get('met_min_medium', 0) + d.get('met_min_high', 0)
        for d in data
    ])
    avg_daily_met = total_met / len(data) if data else 0

    high_met = sum([d.get('met_min_high', 0) for d in data])
    medium_met = sum([d.get('met_min_medium', 0) for d in data])

    return f"""MET Minutes Analysis (Last {days} Days):

Total MET Minutes: {total_met:,}
Average Daily MET Minutes: {avg_daily_met:.0f}

Intensity Breakdown:
- High Intensity MET: {high_met:,} min
- Medium Intensity MET: {medium_met:,} min

WHO Recommendations:
- Target: 500-1000 MET-minutes per week
- Your weekly estimate: ~{avg_daily_met * 7:.0f} MET-min

What MET Minutes Mean:
- 1 MET = energy expended sitting quietly
- Walking (3 mph) = ~3.5 METs
- Running (6 mph) = ~10 METs
- Higher MET minutes = more beneficial activity"""
