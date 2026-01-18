"""Readiness and recovery tools for Oura Health Agent.

These tools provide insights into recovery status and exercise readiness.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def check_exercise_readiness(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Check if the user is ready for exercise based on readiness score.

    Use this when the user asks if they should work out, if they're ready
    to exercise, or about their recovery status for training.

    Returns:
        Exercise readiness assessment
    """
    data = await queries.get_latest_readiness(db_session)

    if not data:
        return "No readiness data available. Make sure you wore your ring last night!"

    score = data.get('score', 0)
    hrv_balance = data.get('hrv_balance_score', 50)
    recovery_index = data.get('recovery_index_score', 50)
    resting_hr = data.get('resting_heart_rate', 0)

    if score >= 85:
        recommendation = "Excellent readiness! Great day for high-intensity training or challenging workouts."
    elif score >= 70:
        recommendation = "Good readiness. You can do moderate to intense exercise today."
    elif score >= 50:
        recommendation = "Fair readiness. Consider lighter activity or active recovery."
    else:
        recommendation = "Low readiness. Focus on rest and recovery today. Light stretching or walking is okay."

    return f"""Exercise Readiness Assessment:

Readiness Score: {score}/100

Key Indicators:
- HRV Balance: {hrv_balance}/100 {'(above baseline)' if hrv_balance >= 50 else '(below baseline)'}
- Recovery Index: {recovery_index}/100
- Resting Heart Rate: {resting_hr} bpm

Recommendation: {recommendation}

Training Guidance:
- Score 85+: High intensity, strength training, competitions
- Score 70-84: Normal training, cardio, moderate weights
- Score 50-69: Light exercise, yoga, easy cardio
- Score <50: Rest day, gentle stretching, meditation"""


@tool
async def get_recovery_status(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get detailed recovery status based on multiple metrics.

    Use this when the user asks about their recovery, how recovered they are,
    or their body's recovery state.

    Returns:
        Detailed recovery status
    """
    data = await queries.get_recovery_data(db_session)

    if not data:
        return "No recovery data available."

    return f"""Recovery Status:

Overall Readiness: {data.get('score', 'N/A')}/100

Recovery Components:
- Previous Night Sleep: {data.get('sleep_score', 'N/A')}/100
- Previous Day Activity: {data.get('activity_balance_score', 'N/A')}/100
- Body Temperature: {data.get('temperature_deviation', 'N/A')}°C from baseline
- HRV Balance: {data.get('hrv_balance_score', 'N/A')}/100
- Resting HR: {data.get('resting_heart_rate', 'N/A')} bpm

Recovery Insights:
{data.get('recovery_insight', 'Your body is processing the activities and sleep from previous days.')}

What Affects Recovery:
- Sleep quality and duration
- Training load from previous days
- Stress levels
- Alcohol consumption
- Illness or infection"""


@tool
async def get_readiness_trends(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get readiness score trends over time.

    Use this when the user asks about their readiness patterns, how their
    recovery has been trending, or readiness over the week.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Readiness trend analysis
    """
    data = await queries.get_readiness_trends(db_session, days)

    if not data or len(data) == 0:
        return f"No readiness data found for the last {days} days."

    scores = [d.get('score', 0) for d in data if d.get('score')]
    avg_score = sum(scores) / len(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0

    trend_data = "\n".join([
        f"- {d.get('day', 'N/A')}: Score {d.get('score', 'N/A')}"
        for d in data[:7]
    ])

    # Determine trend direction
    if len(scores) >= 3:
        recent_avg = sum(scores[:3]) / 3
        older_avg = sum(scores[-3:]) / 3
        trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
    else:
        trend = "insufficient data for trend"

    return f"""Readiness Trends (Last {days} Days):

Average Readiness: {avg_score:.0f}/100
Score Range: {min_score} - {max_score}
Trend: {trend.title()}

Daily Breakdown:
{trend_data}

Interpretation:
- Scores 85+: Peak performance days
- Scores 70-84: Normal/good days
- Scores 50-69: Recovery needed
- Scores <50: Rest day recommended"""


@tool
async def get_readiness_contributors(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get breakdown of factors contributing to readiness score.

    Use this when the user asks what's affecting their readiness, why their
    readiness is low/high, or what's impacting their recovery.

    Returns:
        Readiness contributor breakdown
    """
    data = await queries.get_readiness_contributors(db_session)

    if not data:
        return "No readiness contributor data available."

    contributors = [
        ("Previous Night Sleep", data.get('sleep_score', 'N/A')),
        ("Sleep Balance", data.get('sleep_balance_score', 'N/A')),
        ("Previous Day Activity", data.get('activity_balance_score', 'N/A')),
        ("Activity Balance", data.get('activity_balance_score', 'N/A')),
        ("Body Temperature", data.get('body_temperature_score', 'N/A')),
        ("HRV Balance", data.get('hrv_balance_score', 'N/A')),
        ("Recovery Index", data.get('recovery_index_score', 'N/A')),
        ("Resting Heart Rate", data.get('resting_heart_rate_score', 'N/A')),
    ]

    # Find lowest contributors
    valid_contributors = [(name, score) for name, score in contributors if isinstance(score, (int, float))]
    sorted_contributors = sorted(valid_contributors, key=lambda x: x[1])

    lowest = sorted_contributors[:3] if len(sorted_contributors) >= 3 else sorted_contributors

    return f"""Readiness Contributors:

Overall Score: {data.get('score', 'N/A')}/100

Component Scores:
{chr(10).join([f"- {name}: {score}/100" for name, score in contributors if score != 'N/A'])}

Areas to Focus On:
{chr(10).join([f"- {name}: {score}/100 (lowest)" for name, score in lowest])}

Tips to Improve:
- Prioritize sleep consistency and duration
- Balance activity with adequate rest
- Manage stress levels
- Stay hydrated and well-nourished"""


@tool
async def get_temperature_deviation(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get body temperature deviation from baseline over time.

    Use this when the user asks about their body temperature, temperature changes,
    or potential illness indicators.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Temperature deviation analysis
    """
    data = await queries.get_temperature_data(db_session, days)

    if not data or len(data) == 0:
        return f"No temperature data found for the last {days} days."

    temps = [d.get('temperature_deviation', 0) for d in data if d.get('temperature_deviation') is not None]

    if not temps:
        return "Temperature deviation data not available."

    avg_temp = sum(temps) / len(temps)
    max_temp = max(temps)
    min_temp = min(temps)

    temp_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('temperature_deviation', 'N/A'):+.1f}°C"
        for d in data[:7]
    ])

    # Check for concerning patterns
    if max_temp > 1.0:
        concern = "Elevated temperature detected. This could indicate illness, intense training, or hormonal changes."
    elif max_temp > 0.5:
        concern = "Slightly elevated temperatures. Monitor for any other symptoms."
    else:
        concern = "Temperature within normal range."

    return f"""Body Temperature Analysis (Last {days} Days):

Average Deviation: {avg_temp:+.2f}°C from baseline
Range: {min_temp:+.1f}°C to {max_temp:+.1f}°C

Daily Deviations:
{temp_data}

Assessment: {concern}

What Affects Body Temperature:
- Sleep environment
- Alcohol consumption
- Intense exercise
- Illness or infection
- Menstrual cycle (for women)
- Stress and overtraining"""
