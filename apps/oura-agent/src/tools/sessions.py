"""Meditation and breathing session tools for Oura Health Agent.

These tools provide insights into meditation and breathing exercise sessions.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_meditation_sessions(
    days: Annotated[int, "Number of days to look back (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get meditation session data over time.

    Use this when the user asks about their meditation practice, meditation sessions,
    or mindfulness activities.

    Args:
        days: Number of days to look back (default 7)

    Returns:
        Meditation session analysis
    """
    data = await queries.get_sessions(db_session, days, session_type="meditation")

    if not data or len(data) == 0:
        return f"No meditation sessions found in the last {days} days. Consider starting a meditation practice!"

    session_list = "\n".join([
        f"- {s.get('day', 'N/A')}: {s.get('duration', 0)} min - {s.get('type', 'Meditation')}"
        for s in data
    ])

    total_duration = sum([s.get('duration', 0) for s in data])
    avg_duration = total_duration / len(data) if data else 0

    return f"""Meditation Sessions (Last {days} Days):

Total Sessions: {len(data)}
Total Time: {total_duration} minutes
Average Session: {avg_duration:.0f} minutes

Sessions:
{session_list}

Benefits of Regular Meditation:
- Reduced stress and anxiety
- Improved focus and concentration
- Better sleep quality
- Enhanced emotional regulation
- Lower blood pressure

Recommended Practice:
- Start with 5-10 minutes daily
- Gradually increase to 20-30 minutes
- Consistency matters more than duration

Your meditation frequency: {len(data)/days*7:.1f} sessions per week"""


@tool
async def get_breathing_sessions(
    days: Annotated[int, "Number of days to look back (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get breathing exercise session data over time.

    Use this when the user asks about their breathing exercises, breathwork,
    or breathing practice.

    Args:
        days: Number of days to look back (default 7)

    Returns:
        Breathing session analysis
    """
    data = await queries.get_sessions(db_session, days, session_type="breathing")

    if not data or len(data) == 0:
        return f"No breathing sessions found in the last {days} days. Breathing exercises are great for stress relief!"

    session_list = "\n".join([
        f"- {s.get('day', 'N/A')}: {s.get('duration', 0)} min"
        for s in data
    ])

    total_duration = sum([s.get('duration', 0) for s in data])

    return f"""Breathing Sessions (Last {days} Days):

Total Sessions: {len(data)}
Total Time: {total_duration} minutes

Sessions:
{session_list}

Breathing Exercise Benefits:
- Activates parasympathetic nervous system
- Reduces cortisol levels
- Improves HRV over time
- Quick stress relief (even 1-2 minutes helps)

Popular Techniques:
- Box breathing (4-4-4-4)
- 4-7-8 breathing
- Coherent breathing (5 seconds in, 5 seconds out)

Try to incorporate 2-3 short breathing sessions daily for optimal stress management."""


@tool
async def get_session_hr_response(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get heart rate response during recent meditation/breathing sessions.

    Use this when the user asks how their heart rate responds to meditation,
    the physiological effects of their practice, or HR during sessions.

    Returns:
        Heart rate response during sessions
    """
    data = await queries.get_session_hr_response(db_session)

    if not data:
        return "No recent session data with heart rate available."

    sessions_with_hr = [s for s in data if s.get('hr_start') and s.get('hr_end')]

    if not sessions_with_hr:
        return "No sessions with heart rate data available."

    session_analysis = []
    for s in sessions_with_hr[:5]:
        hr_change = s.get('hr_end', 0) - s.get('hr_start', 0)
        session_analysis.append(
            f"- {s.get('type', 'Session')}: Started {s.get('hr_start', 0)} bpm → "
            f"Ended {s.get('hr_end', 0)} bpm ({hr_change:+} bpm)"
        )

    avg_start = sum([s.get('hr_start', 0) for s in sessions_with_hr]) / len(sessions_with_hr)
    avg_end = sum([s.get('hr_end', 0) for s in sessions_with_hr]) / len(sessions_with_hr)
    avg_change = avg_end - avg_start

    return f"""Heart Rate Response During Sessions:

Recent Sessions:
{chr(10).join(session_analysis)}

Average Response:
- Starting HR: {avg_start:.0f} bpm
- Ending HR: {avg_end:.0f} bpm
- Average Change: {avg_change:+.0f} bpm

Interpretation:
{
'Good response - HR decreased during session.' if avg_change < -3 else
'Moderate response - slight HR decrease.' if avg_change < 0 else
'HR remained stable or increased slightly. This can happen with certain practices.'
}

What a Good Response Looks Like:
- Heart rate typically decreases 5-15 bpm during relaxation practices
- Deeper practice = greater HR reduction
- Consistency improves your body's relaxation response

Note: Some breathing techniques (like energizing breathwork) may increase HR intentionally."""
