"""Advanced health metrics tools for Oura Health Agent.

These tools provide insights into VO2 max, cardiovascular age, SpO2, and respiratory metrics.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_vo2_max(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get VO2 max (cardio fitness) estimation.

    Use this when the user asks about their VO2 max, cardio fitness level,
    or aerobic capacity.

    Returns:
        VO2 max analysis
    """
    data = await queries.get_vo2_max(db_session)

    if not data:
        return "No VO2 max data available. This metric requires regular activity and may take a few weeks to calculate."

    vo2 = data.get('vo2_max', 0)
    age = data.get('age', 30)  # Default if not available

    # VO2 max fitness categories (general population)
    if vo2 >= 50:
        fitness = "Excellent - athlete level"
    elif vo2 >= 42:
        fitness = "Good - above average"
    elif vo2 >= 35:
        fitness = "Fair - average"
    elif vo2 >= 28:
        fitness = "Below average"
    else:
        fitness = "Low - room for improvement"

    return f"""VO2 Max Analysis:

Estimated VO2 Max: {vo2:.1f} mL/kg/min
Fitness Level: {fitness}

What VO2 Max Means:
- Measures your body's ability to use oxygen during exercise
- Higher values indicate better cardiovascular fitness
- Improves with consistent aerobic exercise

Typical VO2 Max Ranges (Adults):
- Excellent: 50+ mL/kg/min
- Good: 42-50 mL/kg/min
- Average: 35-42 mL/kg/min
- Below Average: 28-35 mL/kg/min
- Poor: <28 mL/kg/min

Improve VO2 Max:
- Regular aerobic exercise (running, cycling, swimming)
- Interval training (HIIT)
- Consistent training over months
- Progress gradually to avoid injury

Note: This is an estimation based on your Oura data. For precise measurements, consider a lab test."""


@tool
async def get_cardiovascular_age(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get estimated cardiovascular age compared to chronological age.

    Use this when the user asks about their heart age, cardiovascular age,
    or how their heart health compares to their age.

    Returns:
        Cardiovascular age assessment
    """
    data = await queries.get_cardiovascular_age(db_session)

    if not data:
        return "No cardiovascular age data available. This metric requires several weeks of data to calculate."

    cardio_age = data.get('cardiovascular_age', 0)
    chronological_age = data.get('chronological_age', 0)
    diff = cardio_age - chronological_age

    if diff <= -5:
        assessment = "Excellent! Your heart is significantly younger than your actual age."
    elif diff <= 0:
        assessment = "Great! Your heart age is at or below your actual age."
    elif diff <= 5:
        assessment = "Your heart age is slightly above your actual age. Room for improvement."
    else:
        assessment = "Your heart age is elevated. Consider lifestyle changes and consult a doctor."

    return f"""Cardiovascular Age Assessment:

Your Chronological Age: {chronological_age} years
Your Cardiovascular Age: {cardio_age} years
Difference: {diff:+} years

Assessment: {assessment}

What This Means:
- Cardiovascular age reflects heart health based on various biomarkers
- A lower cardio age than chronological age indicates good heart health
- This can change with lifestyle modifications

Factors That Affect Cardiovascular Age:
- Resting heart rate
- Blood pressure
- Physical activity levels
- Sleep quality
- Body composition
- Smoking and alcohol use

Improve Your Heart Age:
- Regular aerobic exercise
- Maintain healthy weight
- Quality sleep
- Stress management
- Heart-healthy diet

Note: This is an estimation. For a comprehensive assessment, consult your healthcare provider."""


@tool
async def get_spo2_levels(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get blood oxygen (SpO2) levels during sleep.

    Use this when the user asks about their blood oxygen, SpO2, oxygen saturation,
    or breathing during sleep.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        SpO2 analysis
    """
    data = await queries.get_spo2_data(db_session, days)

    if not data or len(data) == 0:
        return f"No SpO2 data found for the last {days} days. Make sure SpO2 tracking is enabled in your Oura app."

    averages = [d.get('spo2_average', 0) for d in data if d.get('spo2_average')]
    avg_spo2 = sum(averages) / len(averages) if averages else 0

    spo2_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('spo2_average', 'N/A')}% avg"
        for d in data[:7]
    ])

    # Assessment based on average SpO2
    if avg_spo2 >= 95:
        status = "Normal - healthy oxygen levels"
    elif avg_spo2 >= 90:
        status = "Slightly low - consider monitoring"
    else:
        status = "Low - consult a healthcare provider"

    return f"""Blood Oxygen (SpO2) Analysis (Last {days} Days):

Average SpO2: {avg_spo2:.1f}%
Status: {status}

Nightly Readings:
{spo2_data}

Normal SpO2 Ranges:
- Normal: 95-100%
- Slightly Low: 90-94%
- Low: Below 90% (consult doctor)

What Affects SpO2:
- Sleep position
- Altitude
- Respiratory conditions
- Sleep apnea
- Nasal congestion

Note: If you consistently see readings below 95%, consider discussing with your healthcare provider."""


@tool
async def get_breathing_disturbance(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Check for breathing disturbances during sleep.

    Use this when the user asks about breathing issues, sleep apnea indicators,
    or breathing disturbances during sleep.

    Returns:
        Breathing disturbance analysis
    """
    data = await queries.get_breathing_disturbance_data(db_session)

    if not data:
        return "No breathing disturbance data available."

    disturbance_index = data.get('breathing_disturbance_index', 0)

    if disturbance_index < 5:
        severity = "Normal - minimal disturbances"
        recommendation = "Your breathing during sleep appears normal."
    elif disturbance_index < 15:
        severity = "Mild - some disturbances detected"
        recommendation = "Consider sleep position changes or consult a doctor if symptoms persist."
    elif disturbance_index < 30:
        severity = "Moderate - noticeable disturbances"
        recommendation = "Consider discussing with a healthcare provider about a sleep study."
    else:
        severity = "Severe - significant disturbances"
        recommendation = "Please consult a healthcare provider. A sleep study may be recommended."

    return f"""Breathing Disturbance Analysis:

Breathing Disturbance Index: {disturbance_index:.1f} events/hour
Severity: {severity}

SpO2 During Sleep:
- Average: {data.get('spo2_average', 'N/A')}%
- Minimum: {data.get('spo2_min', 'N/A')}%

Time Below 90% SpO2: {data.get('time_below_90', 'N/A')} minutes

{recommendation}

What This Indicates:
- Breathing disturbances can affect sleep quality
- May indicate sleep apnea or other conditions
- Position, weight, and allergies can contribute

Important: Oura provides indicators only. For diagnosis of sleep disorders, a clinical sleep study is required."""


@tool
async def get_respiratory_rate(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get respiratory rate during sleep over time.

    Use this when the user asks about their breathing rate, respiratory rate,
    or breaths per minute during sleep.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Respiratory rate analysis
    """
    data = await queries.get_respiratory_data(db_session, days)

    if not data or len(data) == 0:
        return f"No respiratory rate data found for the last {days} days."

    rates = [d.get('average_breath', 0) for d in data if d.get('average_breath')]
    avg_rate = sum(rates) / len(rates) if rates else 0
    min_rate = min(rates) if rates else 0
    max_rate = max(rates) if rates else 0

    resp_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('average_breath', 'N/A')} breaths/min"
        for d in data[:7]
    ])

    # Assessment
    if 12 <= avg_rate <= 20:
        status = "Normal range"
    elif avg_rate < 12:
        status = "Below normal - may indicate relaxed state or athlete"
    else:
        status = "Above normal - may indicate stress, illness, or elevated temperature"

    return f"""Respiratory Rate Analysis (Last {days} Days):

Average Respiratory Rate: {avg_rate:.1f} breaths/min
Range: {min_rate:.1f} - {max_rate:.1f} breaths/min
Status: {status}

Nightly Readings:
{resp_data}

Normal Ranges:
- Adults: 12-20 breaths/min during sleep
- Athletes may have lower rates

Elevated Respiratory Rate May Indicate:
- Fever or illness
- Stress or anxiety
- Respiratory conditions
- High altitude

Tracking respiratory rate can help detect early signs of illness before other symptoms appear."""
