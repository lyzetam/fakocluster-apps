"""Utility tools for Oura Health Agent.

These tools provide access to user profile, ring info, and other utility data.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_user_profile(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get the user's Oura profile information.

    Use this when the user asks about their profile, personal info,
    or account settings.

    Returns:
        User profile information
    """
    data = await queries.get_personal_info(db_session)

    if not data:
        return "No profile information available."

    return f"""Your Oura Profile:

Personal Information:
- Age: {data.get('age', 'N/A')} years
- Gender: {data.get('biological_sex', 'N/A')}
- Height: {data.get('height', 'N/A')} cm
- Weight: {data.get('weight', 'N/A')} kg
- Email: {data.get('email', 'N/A')}

Account:
- Member Since: {data.get('created_at', 'N/A')}
- Oura Member: {'Yes' if data.get('is_member') else 'No'}

Note: This information is used to personalize your health insights and recommendations."""


@tool
async def get_ring_info(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get information about the user's Oura ring.

    Use this when the user asks about their ring, ring model,
    or ring configuration.

    Returns:
        Oura ring information
    """
    data = await queries.get_ring_configuration(db_session)

    if not data:
        return "No ring configuration information available."

    return f"""Your Oura Ring:

Ring Details:
- Model: {data.get('model', 'N/A')}
- Color: {data.get('color', 'N/A')}
- Size: {data.get('size', 'N/A')}
- Firmware Version: {data.get('firmware_version', 'N/A')}

Configuration:
- Hardware Type: {data.get('hardware_type', 'N/A')}
- Setup Date: {data.get('set_up_at', 'N/A')}

Battery & Status:
- Last Sync: {data.get('last_sync', 'N/A')}

Tip: For best accuracy, wear your ring snugly with the sensors on your palm side."""


@tool
async def get_rest_mode_history(
    days: Annotated[int, "Number of days to look back (default 30)"] = 30,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get rest mode period history.

    Use this when the user asks about rest mode, sick days tracked,
    or recovery periods.

    Args:
        days: Number of days to look back (default 30)

    Returns:
        Rest mode history
    """
    data = await queries.get_rest_mode_periods(db_session, days)

    if not data or len(data) == 0:
        return f"No rest mode periods recorded in the last {days} days. Rest mode is used to track illness or recovery periods."

    period_list = []
    for period in data:
        start = period.get('start_time', 'N/A')
        end = period.get('end_time', 'Ongoing')
        if isinstance(start, datetime):
            start = start.strftime('%Y-%m-%d')
        if isinstance(end, datetime):
            end = end.strftime('%Y-%m-%d')

        period_list.append(
            f"- {start} to {end}: {period.get('duration_days', 'N/A')} days"
        )

    total_days = sum([p.get('duration_days', 0) for p in data])

    return f"""Rest Mode History (Last {days} Days):

Rest Periods:
{chr(10).join(period_list)}

Total Rest Days: {total_days}

What is Rest Mode?
- Use when you're sick or recovering
- Oura adjusts expectations during rest mode
- Goals and targets are paused
- Data is still tracked for recovery insights

Enable rest mode in the Oura app when you're unwell or need extended recovery."""


@tool
async def get_user_tags(
    days: Annotated[int, "Number of days to look back (default 14)"] = 14,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get user-added tags from the Oura app.

    Use this when the user asks about their tags, notes they've added,
    or tracked events.

    Args:
        days: Number of days to look back (default 14)

    Returns:
        User tags and notes
    """
    data = await queries.get_tags(db_session, days)

    if not data or len(data) == 0:
        return (
            f"No tags found in the last {days} days.\n\n"
            "You can add tags in the Oura app to track factors that might affect your health, like:\n"
            "- Alcohol consumption\n"
            "- Caffeine intake\n"
            "- Late meals\n"
            "- Stressful events\n"
            "- Exercise\n"
            "\nTags help identify patterns between lifestyle factors and your health data."
        )

    # Group tags by type
    tag_types = {}
    for tag in data:
        tag_type = tag.get('tag_type', 'other')
        if tag_type not in tag_types:
            tag_types[tag_type] = []
        tag_types[tag_type].append(tag)

    tag_summary = []
    for tag_type, tags in tag_types.items():
        dates = [t.get('day', 'N/A') for t in tags]
        tag_summary.append(f"- {tag_type.title()}: {len(tags)} times ({', '.join(dates[:3])}...)")

    tag_list = "\n".join([
        f"- {t.get('day', 'N/A')}: {t.get('tag_type', 'N/A')} {t.get('note', '') or ''}"
        for t in data[:10]
    ])

    return f"""Your Tags (Last {days} Days):

Summary by Type:
{chr(10).join(tag_summary)}

Recent Tags:
{tag_list}

Use tags to:
- Track lifestyle factors (alcohol, caffeine, late meals)
- Note significant events (travel, illness, stress)
- Find correlations with your health data

I can help analyze how your tags relate to your health metrics!"""


@tool
async def get_data_collection_status(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Check the status of data collection from Oura.

    Use this when the user asks if their data is up to date, when data was
    last synced, or about data freshness.

    Returns:
        Data collection status
    """
    data = await queries.get_collection_status(db_session)

    if not data:
        return "Unable to retrieve data collection status."

    # Format data freshness by type
    data_types = {
        "sleep": data.get('latest_sleep', 'N/A'),
        "activity": data.get('latest_activity', 'N/A'),
        "readiness": data.get('latest_readiness', 'N/A'),
        "heart_rate": data.get('latest_heart_rate', 'N/A'),
        "workouts": data.get('latest_workout', 'N/A'),
    }

    status_list = []
    for dtype, latest in data_types.items():
        if latest and latest != 'N/A':
            if isinstance(latest, datetime):
                age = (datetime.now() - latest).days
                status = "Current" if age <= 1 else f"{age} days old"
                status_list.append(f"- {dtype.title()}: {status} (last: {latest.strftime('%Y-%m-%d')})")
            else:
                status_list.append(f"- {dtype.title()}: {latest}")
        else:
            status_list.append(f"- {dtype.title()}: No data")

    total_records = data.get('total_records', 0)
    oldest_data = data.get('oldest_record', 'N/A')

    return f"""Data Collection Status:

Data Freshness:
{chr(10).join(status_list)}

Collection Summary:
- Total Records: {total_records:,}
- Data Range: {oldest_data} to present
- Last Collection: {data.get('last_collection', 'N/A')}

Data Collection Info:
- Data is collected from Oura API periodically
- Sync your ring with the Oura app for latest data
- Some metrics update daily, others in real-time

If data seems stale, ensure:
1. Your ring is charged and synced
2. The Oura app has latest data
3. The data collector service is running"""
