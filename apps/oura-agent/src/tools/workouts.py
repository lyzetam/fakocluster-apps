"""Workout tracking tools for Oura Health Agent.

These tools provide insights into logged workouts and exercise sessions.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_recent_workouts(
    days: Annotated[int, "Number of days to look back (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get a list of recent workouts.

    Use this when the user asks about their recent workouts, exercise history,
    or what workouts they've done.

    Args:
        days: Number of days to look back (default 7)

    Returns:
        List of recent workouts
    """
    data = await queries.get_recent_workouts(db_session, days)

    if not data or len(data) == 0:
        return f"No workouts recorded in the last {days} days. Log your workouts in the Oura app!"

    workout_list = []
    for w in data:
        workout_list.append(
            f"- {w.get('day', 'N/A')}: {w.get('activity', 'Unknown')} - "
            f"{w.get('duration', 0)} min, {w.get('calories', 0)} kcal, "
            f"Intensity: {w.get('intensity', 'N/A')}"
        )

    total_duration = sum([w.get('duration', 0) for w in data])
    total_calories = sum([w.get('calories', 0) for w in data])

    return f"""Recent Workouts (Last {days} Days):

{chr(10).join(workout_list)}

Summary:
- Total Workouts: {len(data)}
- Total Duration: {total_duration} minutes
- Total Calories Burned: {total_calories} kcal
- Average per Workout: {total_duration/len(data):.0f} min"""


@tool
async def get_workout_summary(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get a summary of workout frequency and patterns.

    Use this when the user asks how often they exercise, their workout frequency,
    or general exercise patterns.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Workout frequency and pattern summary
    """
    data = await queries.get_workout_summary(db_session, days)

    if not data:
        return f"No workout data found for the last {days} days."

    return f"""Workout Summary (Last {days} Days):

Total Workouts: {data.get('total_workouts', 0)}
Workout Frequency: {data.get('workouts_per_week', 0):.1f} per week
Total Exercise Time: {data.get('total_duration', 0)} minutes
Average Workout Duration: {data.get('avg_duration', 0):.0f} minutes

Activity Types:
{chr(10).join([f"- {t}: {c} sessions" for t, c in data.get('activity_breakdown', {}).items()])}

Intensity Distribution:
- Low Intensity: {data.get('low_intensity_pct', 0):.0f}%
- Medium Intensity: {data.get('medium_intensity_pct', 0):.0f}%
- High Intensity: {data.get('high_intensity_pct', 0):.0f}%

Recommendations:
- Target: 3-5 workouts per week
- Your status: {'On track!' if data.get('workouts_per_week', 0) >= 3 else 'Consider adding more workouts'}"""


@tool
async def get_workout_by_type(
    activity_type: Annotated[str, "Type of workout (e.g., 'running', 'cycling', 'strength')"],
    days: Annotated[int, "Number of days to look back (default 30)"] = 30,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get workouts filtered by activity type.

    Use this when the user asks about specific workout types like running,
    cycling, strength training, etc.

    Args:
        activity_type: Type of workout to filter by
        days: Number of days to look back (default 30)

    Returns:
        Workouts of the specified type
    """
    data = await queries.get_workouts_by_type(db_session, activity_type, days)

    if not data or len(data) == 0:
        return f"No {activity_type} workouts found in the last {days} days."

    workout_list = []
    for w in data:
        workout_list.append(
            f"- {w.get('day', 'N/A')}: {w.get('duration', 0)} min, "
            f"{w.get('calories', 0)} kcal, HR avg: {w.get('avg_hr', 'N/A')} bpm"
        )

    total_duration = sum([w.get('duration', 0) for w in data])
    total_calories = sum([w.get('calories', 0) for w in data])
    avg_duration = total_duration / len(data) if data else 0

    return f"""{activity_type.title()} Workouts (Last {days} Days):

{chr(10).join(workout_list)}

Summary:
- Total Sessions: {len(data)}
- Total Duration: {total_duration} minutes
- Average Duration: {avg_duration:.0f} minutes
- Total Calories: {total_calories} kcal"""


@tool
async def get_workout_intensity_distribution(
    days: Annotated[int, "Number of days to analyze (default 30)"] = 30,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Analyze workout intensity distribution over time.

    Use this when the user asks about their workout intensity, if they're
    doing enough high intensity exercise, or their training load.

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Workout intensity analysis
    """
    data = await queries.get_workout_intensity(db_session, days)

    if not data:
        return f"No workout intensity data found for the last {days} days."

    low = data.get('low_intensity_time', 0)
    medium = data.get('medium_intensity_time', 0)
    high = data.get('high_intensity_time', 0)
    total = low + medium + high

    if total == 0:
        return "No workout time recorded. Log your workouts in the Oura app!"

    return f"""Workout Intensity Distribution (Last {days} Days):

Total Exercise Time: {total} minutes

Intensity Breakdown:
- Low Intensity: {low} min ({low/total*100:.0f}%)
- Medium Intensity: {medium} min ({medium/total*100:.0f}%)
- High Intensity: {high} min ({high/total*100:.0f}%)

Heart Rate Zones:
- Zone 2 (Aerobic): {data.get('zone2_time', 'N/A')} min
- Zone 3 (Tempo): {data.get('zone3_time', 'N/A')} min
- Zone 4 (Threshold): {data.get('zone4_time', 'N/A')} min
- Zone 5 (Max): {data.get('zone5_time', 'N/A')} min

Recommendations:
- 80% should be low/medium intensity
- 20% should be high intensity
- Your high intensity ratio: {high/total*100:.0f}%

Training Balance: {
'Well balanced' if 15 <= high/total*100 <= 25 else
'Consider more high intensity' if high/total*100 < 15 else
'Consider more recovery days'
}"""
