"""Sleep analysis tools for Oura Health Agent.

These tools provide insights into sleep patterns, quality, and recommendations.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_last_night_sleep(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get a summary of last night's sleep including duration, quality, and stages.

    Use this when the user asks about their recent sleep, how they slept,
    or general sleep questions without a specific date.

    Returns:
        Summary of last night's sleep data
    """
    data = await queries.get_last_night_sleep(db_session)

    if not data:
        return "No sleep data found for last night. Make sure you wore your Oura ring while sleeping."

    return f"""Last Night's Sleep Summary:
- Total Sleep: {data.get('total_sleep_duration', 'N/A')} hours
- Sleep Score: {data.get('score', 'N/A')}/100
- Bedtime: {data.get('bedtime_start', 'N/A')}
- Wake Time: {data.get('bedtime_end', 'N/A')}
- Time in Bed: {data.get('time_in_bed', 'N/A')} hours
- Sleep Efficiency: {data.get('efficiency', 'N/A')}%

Sleep Stages:
- Deep Sleep: {data.get('deep_sleep', 'N/A')} min ({data.get('deep_sleep_pct', 'N/A')}%)
- REM Sleep: {data.get('rem_sleep', 'N/A')} min ({data.get('rem_sleep_pct', 'N/A')}%)
- Light Sleep: {data.get('light_sleep', 'N/A')} min ({data.get('light_sleep_pct', 'N/A')}%)
- Awake: {data.get('awake', 'N/A')} min

Additional Metrics:
- Average Heart Rate: {data.get('average_heart_rate', 'N/A')} bpm
- Lowest Heart Rate: {data.get('lowest_heart_rate', 'N/A')} bpm
- HRV Average: {data.get('average_hrv', 'N/A')} ms
- Respiratory Rate: {data.get('average_breath', 'N/A')} breaths/min
- Restfulness: {data.get('restless_periods', 'N/A')} restless periods"""


@tool
async def get_sleep_quality(
    date_str: Annotated[str, "Date in YYYY-MM-DD format"],
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get sleep quality data for a specific date.

    Use this when the user asks about sleep on a particular day.

    Args:
        date_str: The date to check sleep for (YYYY-MM-DD)

    Returns:
        Sleep quality data for the specified date
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return f"Invalid date format: {date_str}. Please use YYYY-MM-DD format."

    data = await queries.get_sleep_by_date(db_session, target_date)

    if not data:
        return f"No sleep data found for {date_str}."

    return f"""Sleep Quality for {date_str}:
- Sleep Score: {data.get('score', 'N/A')}/100
- Total Sleep: {data.get('total_sleep_duration', 'N/A')} hours
- Efficiency: {data.get('efficiency', 'N/A')}%
- Deep Sleep: {data.get('deep_sleep', 'N/A')} min
- REM Sleep: {data.get('rem_sleep', 'N/A')} min
- Latency: {data.get('latency', 'N/A')} min to fall asleep
- Restfulness Score: {data.get('score_disturbances', 'N/A')}/100"""


@tool
async def get_sleep_trends(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get sleep score trends over a period of time.

    Use this when the user asks about their sleep patterns, weekly sleep,
    or how their sleep has been trending.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Sleep trend analysis
    """
    data = await queries.get_sleep_trends(db_session, days)

    if not data or len(data) == 0:
        return f"No sleep data found for the last {days} days."

    scores = [d.get('score', 0) for d in data if d.get('score')]
    durations = [d.get('total_sleep_duration', 0) for d in data if d.get('total_sleep_duration')]

    avg_score = sum(scores) / len(scores) if scores else 0
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0

    trend_data = "\n".join([
        f"- {d.get('day', 'N/A')}: Score {d.get('score', 'N/A')}, {d.get('total_sleep_duration', 'N/A')}h"
        for d in data[:7]  # Show last 7 entries
    ])

    return f"""Sleep Trends (Last {days} Days):

Average Sleep Score: {avg_score:.0f}/100
Average Sleep Duration: {avg_duration:.1f} hours
Score Range: {min_score} - {max_score}
Data Points: {len(scores)} nights

Recent Nights:
{trend_data}

Interpretation:
- Scores 85+: Excellent sleep
- Scores 70-84: Good sleep
- Scores 50-69: Fair sleep
- Scores below 50: Poor sleep"""


@tool
async def get_sleep_stages_breakdown(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get a breakdown of sleep stages (deep, REM, light) over time.

    Use this when the user asks about deep sleep, REM sleep, sleep stages,
    or sleep architecture.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Sleep stages breakdown
    """
    data = await queries.get_sleep_stages(db_session, days)

    if not data or len(data) == 0:
        return f"No sleep stage data found for the last {days} days."

    deep_times = [d.get('deep_sleep', 0) for d in data if d.get('deep_sleep') is not None]
    rem_times = [d.get('rem_sleep', 0) for d in data if d.get('rem_sleep') is not None]
    light_times = [d.get('light_sleep', 0) for d in data if d.get('light_sleep') is not None]

    avg_deep = sum(deep_times) / len(deep_times) if deep_times else 0
    avg_rem = sum(rem_times) / len(rem_times) if rem_times else 0
    avg_light = sum(light_times) / len(light_times) if light_times else 0

    return f"""Sleep Stages Breakdown (Last {days} Days):

Average Deep Sleep: {avg_deep:.0f} minutes ({avg_deep/60:.1f} hours)
Average REM Sleep: {avg_rem:.0f} minutes ({avg_rem/60:.1f} hours)
Average Light Sleep: {avg_light:.0f} minutes ({avg_light/60:.1f} hours)

Recommendations:
- Deep Sleep Target: 60-90 minutes (13-23% of total sleep)
- REM Sleep Target: 90-120 minutes (20-25% of total sleep)
- Light Sleep: Typically 50% of total sleep

Your Averages vs Targets:
- Deep Sleep: {'On track' if avg_deep >= 60 else 'Below target'}
- REM Sleep: {'On track' if avg_rem >= 90 else 'Below target'}"""


@tool
async def get_sleep_efficiency_analysis(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Analyze sleep efficiency (time asleep vs time in bed) over time.

    Use this when the user asks about sleep efficiency, time awake in bed,
    or how well they're sleeping.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Sleep efficiency analysis
    """
    data = await queries.get_sleep_efficiency(db_session, days)

    if not data or len(data) == 0:
        return f"No sleep efficiency data found for the last {days} days."

    efficiencies = [d.get('efficiency', 0) for d in data if d.get('efficiency')]
    avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0

    latencies = [d.get('latency', 0) for d in data if d.get('latency') is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    return f"""Sleep Efficiency Analysis (Last {days} Days):

Average Sleep Efficiency: {avg_efficiency:.0f}%
Average Sleep Latency: {avg_latency:.0f} minutes

Efficiency Interpretation:
- 90%+ : Excellent efficiency
- 85-89%: Good efficiency
- 80-84%: Fair efficiency
- Below 80%: Consider sleep hygiene improvements

Your Status: {'Excellent' if avg_efficiency >= 90 else 'Good' if avg_efficiency >= 85 else 'Fair' if avg_efficiency >= 80 else 'Needs improvement'}

Tips for Better Efficiency:
- Go to bed only when sleepy
- Keep a consistent sleep schedule
- Limit screen time before bed
- Keep bedroom cool and dark"""


@tool
async def get_optimal_sleep_time(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get recommendations for optimal bedtime based on sleep patterns.

    Use this when the user asks when they should go to bed, their ideal
    bedtime, or optimal sleep schedule.

    Returns:
        Optimal bedtime recommendations
    """
    data = await queries.get_sleep_time_recommendations(db_session)

    if not data:
        return "Not enough sleep data to determine optimal sleep time. Need at least 7 days of data."

    return f"""Optimal Sleep Time Analysis:

Based on your sleep patterns:

Recommended Bedtime: {data.get('recommended_bedtime', 'N/A')}
Recommended Wake Time: {data.get('recommended_wake_time', 'N/A')}

Your Patterns:
- Average Bedtime: {data.get('avg_bedtime', 'N/A')}
- Average Wake Time: {data.get('avg_wake_time', 'N/A')}
- Best Sleep Score Days: {data.get('best_bedtime_range', 'N/A')}

Consistency Score: {data.get('consistency_score', 'N/A')}/100

Recommendation: {data.get('recommendation', 'Maintain consistent sleep and wake times for better sleep quality.')}"""
