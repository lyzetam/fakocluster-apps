"""Heart rate and HRV analysis tools for Oura Health Agent.

These tools provide insights into heart rate variability and cardiovascular metrics.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_resting_heart_rate(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get resting heart rate data over time.

    Use this when the user asks about their resting heart rate, RHR trends,
    or cardiovascular baseline.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Resting heart rate analysis
    """
    data = await queries.get_resting_hr_data(db_session, days)

    if not data or len(data) == 0:
        return f"No resting heart rate data found for the last {days} days."

    hrs = [d.get('resting_heart_rate', 0) for d in data if d.get('resting_heart_rate')]
    avg_hr = sum(hrs) / len(hrs) if hrs else 0
    min_hr = min(hrs) if hrs else 0
    max_hr = max(hrs) if hrs else 0

    hr_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('resting_heart_rate', 'N/A')} bpm"
        for d in data[:7]
    ])

    # Determine fitness level based on RHR
    if avg_hr < 50:
        fitness = "Athlete level - excellent cardiovascular fitness"
    elif avg_hr < 60:
        fitness = "Excellent - above average fitness"
    elif avg_hr < 70:
        fitness = "Good - average fitness level"
    elif avg_hr < 80:
        fitness = "Fair - room for improvement"
    else:
        fitness = "Elevated - consider consulting a doctor"

    return f"""Resting Heart Rate Analysis (Last {days} Days):

Average RHR: {avg_hr:.0f} bpm
Range: {min_hr} - {max_hr} bpm

Daily Measurements:
{hr_data}

Fitness Assessment: {fitness}

Normal RHR Ranges:
- Athletes: 40-50 bpm
- Excellent: 50-60 bpm
- Good: 60-70 bpm
- Average: 70-80 bpm
- Below Average: 80+ bpm

Note: Elevated RHR can indicate stress, poor sleep, illness, or dehydration."""


@tool
async def get_hrv_analysis(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get heart rate variability (HRV) analysis over time.

    Use this when the user asks about HRV, heart rate variability,
    autonomic nervous system balance, or stress recovery.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        HRV analysis
    """
    data = await queries.get_hrv_data(db_session, days)

    if not data or len(data) == 0:
        return f"No HRV data found for the last {days} days."

    hrvs = [d.get('average_hrv', 0) for d in data if d.get('average_hrv')]
    avg_hrv = sum(hrvs) / len(hrvs) if hrvs else 0
    min_hrv = min(hrvs) if hrvs else 0
    max_hrv = max(hrvs) if hrvs else 0

    hrv_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('average_hrv', 'N/A')} ms"
        for d in data[:7]
    ])

    # Trend analysis
    if len(hrvs) >= 3:
        recent_avg = sum(hrvs[:3]) / 3
        older_avg = sum(hrvs[-3:]) / 3
        trend = "increasing (positive)" if recent_avg > older_avg else "decreasing (concerning)" if recent_avg < older_avg else "stable"
    else:
        trend = "insufficient data"

    return f"""HRV Analysis (Last {days} Days):

Average HRV: {avg_hrv:.0f} ms
Range: {min_hrv} - {max_hrv} ms
Trend: {trend}

Daily Measurements:
{hrv_data}

What HRV Means:
- Higher HRV generally indicates better recovery and fitness
- Lower HRV may indicate stress, fatigue, or illness
- Personal baseline matters more than absolute numbers

Factors That Affect HRV:
- Sleep quality and duration
- Alcohol consumption (decreases HRV)
- Exercise recovery
- Stress and anxiety
- Hydration status

Note: HRV is highly individual. Track your personal trends rather than comparing to others."""


@tool
async def get_heart_rate_during_sleep(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get heart rate data during last night's sleep.

    Use this when the user asks about their heart rate while sleeping,
    nighttime HR, or sleep heart rate patterns.

    Returns:
        Sleep heart rate analysis
    """
    data = await queries.get_sleep_hr_data(db_session)

    if not data:
        return "No sleep heart rate data available for last night."

    return f"""Sleep Heart Rate Analysis (Last Night):

Average Heart Rate: {data.get('average_heart_rate', 'N/A')} bpm
Lowest Heart Rate: {data.get('lowest_heart_rate', 'N/A')} bpm

Heart Rate Pattern:
- Start of Night: {data.get('hr_start', 'N/A')} bpm
- Mid-Sleep: {data.get('hr_mid', 'N/A')} bpm
- End of Night: {data.get('hr_end', 'N/A')} bpm

HRV During Sleep: {data.get('average_hrv', 'N/A')} ms

Interpretation:
- Lowest HR typically occurs 3-4 hours into sleep
- HR should gradually decrease then rise before waking
- Elevated nighttime HR may indicate stress, illness, or alcohol

Your lowest HR of {data.get('lowest_heart_rate', 'N/A')} bpm indicates {'good' if data.get('lowest_heart_rate', 100) < 60 else 'fair'} cardiovascular recovery during sleep."""


@tool
async def get_hrv_balance(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Check HRV balance relative to personal baseline.

    Use this when the user asks if their HRV is above or below baseline,
    their HRV balance, or autonomic nervous system status.

    Returns:
        HRV balance assessment
    """
    data = await queries.get_hrv_balance(db_session)

    if not data:
        return "No HRV balance data available. Need at least 2 weeks of data to establish baseline."

    current = data.get('current_hrv', 0)
    baseline = data.get('baseline_hrv', 0)
    balance_score = data.get('hrv_balance_score', 50)

    if baseline > 0:
        diff = current - baseline
        pct_diff = (diff / baseline) * 100
    else:
        diff = 0
        pct_diff = 0

    if balance_score >= 75:
        status = "Above baseline - excellent recovery state"
    elif balance_score >= 50:
        status = "At baseline - normal recovery"
    elif balance_score >= 25:
        status = "Below baseline - may need extra recovery"
    else:
        status = "Significantly below baseline - prioritize rest"

    return f"""HRV Balance Assessment:

Current HRV: {current} ms
Baseline HRV: {baseline} ms
Difference: {diff:+.0f} ms ({pct_diff:+.0f}%)

HRV Balance Score: {balance_score}/100

Status: {status}

What This Means:
- Above baseline: Your body is well-recovered, ready for activity
- At baseline: Normal state, proceed with regular activities
- Below baseline: Consider reducing intensity, focus on recovery

Tips for Improving HRV:
- Consistent sleep schedule
- Stress management (meditation, breathing)
- Moderate exercise (avoid overtraining)
- Limit alcohol consumption
- Stay hydrated"""
