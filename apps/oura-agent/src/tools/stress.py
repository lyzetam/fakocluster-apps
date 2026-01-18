"""Stress and resilience tools for Oura Health Agent.

These tools provide insights into stress levels and resilience metrics.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_stress_levels(
    days: Annotated[int, "Number of days to analyze (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get stress level data over time.

    Use this when the user asks about their stress levels, how stressed they've been,
    or stress patterns.

    Args:
        days: Number of days to analyze (default 7)

    Returns:
        Stress level analysis
    """
    data = await queries.get_stress_data(db_session, days)

    if not data or len(data) == 0:
        return f"No stress data found for the last {days} days. Stress tracking requires Oura Gen3."

    stress_data = "\n".join([
        f"- {d.get('day', 'N/A')}: High {d.get('stress_high', 0)} min, "
        f"Recovery {d.get('recovery_time', 0)} min"
        for d in data[:7]
    ])

    total_stress = sum([d.get('stress_high', 0) for d in data])
    total_recovery = sum([d.get('recovery_time', 0) for d in data])
    avg_daily_stress = total_stress / len(data) if data else 0

    return f"""Stress Analysis (Last {days} Days):

Total High Stress Time: {total_stress} minutes
Total Recovery Time: {total_recovery} minutes
Average Daily Stress: {avg_daily_stress:.0f} minutes

Daily Breakdown:
{stress_data}

Stress-Recovery Ratio: {total_stress}:{total_recovery}
{'Good balance' if total_recovery >= total_stress else 'Consider more recovery activities'}

Stress Indicators:
- High stress time reflects periods of elevated sympathetic activity
- Recovery time reflects restorative parasympathetic activity

Tips to Reduce Stress:
- Practice breathing exercises
- Take regular breaks during work
- Engage in light physical activity
- Practice mindfulness or meditation
- Ensure adequate sleep"""


@tool
async def get_stress_recovery_balance(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Analyze the balance between stress and recovery.

    Use this when the user asks about their stress-recovery balance,
    if they're recovering from stress, or about nervous system balance.

    Returns:
        Stress-recovery balance analysis
    """
    data = await queries.get_stress_recovery_balance(db_session)

    if not data:
        return "No stress-recovery data available."

    stress_high = data.get('stress_high', 0)
    recovery = data.get('recovery_time', 0)
    restored = data.get('day_restored', 0)

    # Calculate balance
    total = stress_high + recovery + restored
    if total > 0:
        stress_pct = (stress_high / total) * 100
        recovery_pct = ((recovery + restored) / total) * 100
    else:
        stress_pct = 0
        recovery_pct = 0

    if recovery_pct >= 60:
        balance_status = "Excellent - good recovery balance"
    elif recovery_pct >= 40:
        balance_status = "Good - adequate recovery"
    elif recovery_pct >= 25:
        balance_status = "Fair - could use more recovery time"
    else:
        balance_status = "Needs attention - prioritize recovery"

    return f"""Stress-Recovery Balance (Today):

Time Distribution:
- High Stress: {stress_high} min ({stress_pct:.0f}%)
- Recovery: {recovery} min
- Restored: {restored} min
- Total Recovery: {recovery + restored} min ({recovery_pct:.0f}%)

Balance Status: {balance_status}

Daytime Stress: {data.get('daytime_stress', 'N/A')} events
Restorative Periods: {data.get('restorative_time', 'N/A')} min

Recommendations:
{
'Great job maintaining balance!' if recovery_pct >= 60 else
'Try adding short breathing exercises throughout the day.' if recovery_pct >= 40 else
'Consider a longer break or meditation session today.' if recovery_pct >= 25 else
'Prioritize rest and recovery activities. Your body needs it.'
}"""


@tool
async def get_resilience_status(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get current resilience status and level.

    Use this when the user asks about their resilience, stress handling capacity,
    or overall physiological resilience.

    Returns:
        Resilience status assessment
    """
    data = await queries.get_resilience_data(db_session)

    if not data:
        return "No resilience data available. Resilience tracking requires several weeks of data."

    level = data.get('level', 'Unknown')
    contributors = data.get('contributors', {})

    level_desc = {
        'limited': "Your body may be under significant stress. Focus on recovery.",
        'adequate': "Your resilience is building. Maintain good habits.",
        'solid': "You have good resilience. Your body handles stress well.",
        'strong': "Excellent resilience! Your body recovers quickly from stress.",
        'exceptional': "Outstanding resilience. You're in peak condition for handling challenges."
    }

    return f"""Resilience Status:

Current Level: {level.title()}

{level_desc.get(level.lower(), 'Continue monitoring your resilience trends.')}

Contributing Factors:
- Sleep Consistency: {contributors.get('sleep', 'N/A')}
- Recovery Patterns: {contributors.get('recovery', 'N/A')}
- Activity Balance: {contributors.get('activity', 'N/A')}
- Stress Management: {contributors.get('stress', 'N/A')}

What Resilience Means:
- Resilience reflects how well your body handles and recovers from stress
- Higher resilience = better ability to bounce back from challenges
- Built through consistent sleep, exercise, and recovery practices

Improve Resilience By:
- Maintaining consistent sleep schedules
- Regular moderate exercise
- Stress management practices
- Balanced nutrition and hydration"""


@tool
async def get_resilience_trends(
    days: Annotated[int, "Number of days to analyze (default 14)"] = 14,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get resilience trends over time.

    Use this when the user asks how their resilience has been trending,
    if they're building resilience, or long-term resilience patterns.

    Args:
        days: Number of days to analyze (default 14)

    Returns:
        Resilience trend analysis
    """
    data = await queries.get_resilience_trends(db_session, days)

    if not data or len(data) == 0:
        return f"No resilience trend data found for the last {days} days."

    levels = [d.get('level', '') for d in data if d.get('level')]

    # Count level occurrences
    level_counts = {}
    for level in levels:
        level_counts[level] = level_counts.get(level, 0) + 1

    # Determine trend
    level_order = ['limited', 'adequate', 'solid', 'strong', 'exceptional']
    if len(levels) >= 4:
        recent_levels = levels[:len(levels)//2]
        older_levels = levels[len(levels)//2:]

        def avg_level(lvls):
            indices = [level_order.index(l) for l in lvls if l in level_order]
            return sum(indices) / len(indices) if indices else 0

        recent_avg = avg_level(recent_levels)
        older_avg = avg_level(older_levels)
        trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
    else:
        trend = "insufficient data for trend"

    trend_data = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('level', 'N/A').title()}"
        for d in data[:7]
    ])

    return f"""Resilience Trends (Last {days} Days):

Overall Trend: {trend.title()}

Level Distribution:
{chr(10).join([f"- {level.title()}: {count} days" for level, count in level_counts.items()])}

Recent Readings:
{trend_data}

Building Resilience:
- Resilience improves with consistent healthy habits
- Expect fluctuations - this is normal
- Focus on long-term trends, not daily changes

Your Path Forward:
{
'Great progress! Keep maintaining your current habits.' if trend == 'improving' else
'Stable resilience is good. Consider small optimizations.' if trend == 'stable' else
'Consider reviewing sleep, stress, and recovery habits.' if trend == 'declining' else
'Continue monitoring to establish baseline trends.'
}"""
