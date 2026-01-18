"""Memory operation tools for Oura Health Agent.

These tools allow the agent to interact with memory systems for
storing and retrieving user goals, insights, and past conversations.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def recall_past_insight(
    query: Annotated[str, "Search query to find relevant past conversations"],
    db_session: Annotated[any, "Database session (injected)"],
    episodic_memory: Annotated[any, "EpisodicMemory instance (injected)"],
    user_id: Annotated[str, "Discord user ID (injected)"],
) -> str:
    """Search episodic memory for relevant past health conversations.

    Use this when the user asks about previous discussions, what you told them
    before, or references past conversations about their health.

    Args:
        query: Search query to find relevant past insights

    Returns:
        Relevant past conversations and insights
    """
    results = await episodic_memory.search(
        session=db_session,
        search_text=query,
        user_id=user_id,
        limit=5,
        threshold=0.6,
    )

    if not results:
        return "I don't have any relevant past conversations about that topic. This might be the first time we're discussing it!"

    memories = []
    for entry in results:
        age = (datetime.now() - entry.created_at).days
        age_str = f"{age} days ago" if age > 1 else "yesterday" if age == 1 else "today"
        memories.append(
            f"**{age_str}** (relevance: {entry.similarity:.0%}):\n"
            f"Question: {entry.query or 'N/A'}\n"
            f"Summary: {entry.summary}\n"
            f"Insight: {entry.outcome or 'N/A'}"
        )

    return f"""Past Conversations Related to "{query}":

{chr(10).join(memories)}

Note: These are summaries of our previous discussions. I can provide more specific details if you ask about any of these topics."""


@tool
async def set_health_goal(
    goal_type: Annotated[str, "Type of goal (sleep_duration, step_count, hrv_target, etc.)"],
    target_value: Annotated[Optional[float], "Numeric target value"] = None,
    target_text: Annotated[Optional[str], "Text description of goal"] = None,
    db_session: Annotated[any, "Database session (injected)"] = None,
    long_term_memory: Annotated[any, "LongTermMemory instance (injected)"] = None,
    user_id: Annotated[str, "Discord user ID (injected)"] = None,
) -> str:
    """Set a new health goal for the user.

    Use this when the user wants to set a health goal, like "I want to sleep 8 hours"
    or "My goal is 10,000 steps per day".

    Args:
        goal_type: Type of goal being set
        target_value: Numeric target (optional)
        target_text: Text description of the goal (optional)

    Returns:
        Confirmation of the goal being set
    """
    valid_types = [
        "sleep_duration", "sleep_score", "step_count", "active_calories",
        "hrv_target", "readiness_score", "workout_frequency", "meditation_minutes"
    ]

    if goal_type not in valid_types:
        return (
            f"I don't recognize that goal type. Valid goal types are:\n"
            f"{', '.join(valid_types)}\n\n"
            "Try rephrasing your goal!"
        )

    if target_value is None and target_text is None:
        return "Please specify a target value or description for your goal."

    goal_id = await long_term_memory.set_goal(
        session=db_session,
        user_id=user_id,
        goal_type=goal_type,
        target_value=target_value,
        target_text=target_text,
    )

    if not goal_id:
        return "I had trouble saving that goal. Please try again."

    goal_descriptions = {
        "sleep_duration": "hours of sleep per night",
        "sleep_score": "sleep score",
        "step_count": "daily steps",
        "active_calories": "active calories per day",
        "hrv_target": "HRV target",
        "readiness_score": "readiness score",
        "workout_frequency": "workouts per week",
        "meditation_minutes": "meditation minutes per day",
    }

    desc = goal_descriptions.get(goal_type, goal_type)
    target_str = f"{target_value}" if target_value else target_text

    return f"""Goal Set Successfully!

Your New Goal:
- {desc.title()}: {target_str}

I'll remember this goal and can:
- Track your progress toward it
- Provide relevant insights
- Celebrate when you achieve it!

You can ask me "How am I doing on my goals?" anytime to check progress."""


@tool
async def get_active_goals(
    db_session: Annotated[any, "Database session (injected)"],
    long_term_memory: Annotated[any, "LongTermMemory instance (injected)"],
    user_id: Annotated[str, "Discord user ID (injected)"],
) -> str:
    """Get all active health goals for the user.

    Use this when the user asks about their goals, what they're working toward,
    or wants to see their health targets.

    Returns:
        List of active health goals
    """
    goals = await long_term_memory.get_active_goals(
        session=db_session,
        user_id=user_id,
    )

    if not goals:
        return (
            "You don't have any active health goals set!\n\n"
            "You can set goals by saying things like:\n"
            "- 'I want to sleep 8 hours a night'\n"
            "- 'My step goal is 10,000 per day'\n"
            "- 'I want to meditate 10 minutes daily'"
        )

    goal_descriptions = {
        "sleep_duration": "Sleep Duration",
        "sleep_score": "Sleep Score",
        "step_count": "Daily Steps",
        "active_calories": "Active Calories",
        "hrv_target": "HRV Target",
        "readiness_score": "Readiness Score",
        "workout_frequency": "Workouts per Week",
        "meditation_minutes": "Meditation Minutes",
    }

    goal_list = []
    for goal in goals:
        desc = goal_descriptions.get(goal.goal_type, goal.goal_type)
        target = goal.target_value if goal.target_value else goal.target_text
        days_active = (datetime.now() - goal.created_at).days
        goal_list.append(f"- **{desc}**: {target} (active for {days_active} days)")

    return f"""Your Active Health Goals:

{chr(10).join(goal_list)}

Ask me about specific goals to check your progress, or tell me when you've achieved one!"""


@tool
async def mark_goal_achieved(
    goal_type: Annotated[str, "Type of goal that was achieved"],
    db_session: Annotated[any, "Database session (injected)"],
    long_term_memory: Annotated[any, "LongTermMemory instance (injected)"],
    user_id: Annotated[str, "Discord user ID (injected)"],
) -> str:
    """Mark a health goal as achieved.

    Use this when the user reports achieving a goal or when data shows
    they've consistently met their target.

    Args:
        goal_type: Type of goal that was achieved

    Returns:
        Confirmation of goal achievement
    """
    goals = await long_term_memory.get_active_goals(
        session=db_session,
        user_id=user_id,
    )

    matching_goal = None
    for goal in goals:
        if goal.goal_type == goal_type:
            matching_goal = goal
            break

    if not matching_goal:
        return f"I couldn't find an active goal of type '{goal_type}'. Check your active goals first!"

    success = await long_term_memory.mark_goal_achieved(
        session=db_session,
        goal_id=matching_goal.id,
    )

    if not success:
        return "I had trouble marking that goal as achieved. Please try again."

    return f"""Congratulations! Goal Achieved!

You've successfully achieved your {goal_type.replace('_', ' ')} goal!

This is a great accomplishment. Consider:
- Setting a new, more ambitious goal
- Maintaining this achievement
- Celebrating your progress!

Keep up the excellent work on your health journey!"""


@tool
async def get_user_baselines(
    db_session: Annotated[any, "Database session (injected)"],
    long_term_memory: Annotated[any, "LongTermMemory instance (injected)"],
    user_id: Annotated[str, "Discord user ID (injected)"],
) -> str:
    """Get the user's computed health baselines.

    Use this when the user asks about their baseline metrics, normal values,
    or typical health metrics.

    Returns:
        User's health baselines
    """
    baselines = await long_term_memory.get_baselines(
        session=db_session,
        user_id=user_id,
    )

    if not baselines:
        return (
            "No baselines computed yet. I'll calculate your personal baselines "
            "as we collect more data over time. Check back in a few weeks!"
        )

    baseline_descriptions = {
        "hrv_avg": "Average HRV",
        "resting_hr": "Resting Heart Rate",
        "sleep_efficiency": "Sleep Efficiency",
        "sleep_duration_avg": "Average Sleep Duration",
        "step_count_avg": "Average Daily Steps",
        "readiness_avg": "Average Readiness Score",
        "activity_score_avg": "Average Activity Score",
    }

    baseline_list = []
    for metric, baseline in baselines.items():
        desc = baseline_descriptions.get(metric, metric)
        baseline_list.append(
            f"- **{desc}**: {baseline.baseline_value:.1f} "
            f"(based on {baseline.sample_size} data points)"
        )

    return f"""Your Personal Health Baselines:

{chr(10).join(baseline_list)}

These baselines represent your typical values and are used to:
- Detect deviations from your normal
- Personalize recommendations
- Track long-term progress

Baselines are updated periodically as new data is collected."""


@tool
async def save_insight(
    insight: Annotated[str, "Key health insight to save"],
    db_session: Annotated[any, "Database session (injected)"],
    episodic_memory: Annotated[any, "EpisodicMemory instance (injected)"],
    user_id: Annotated[str, "Discord user ID (injected)"],
    session_id: Annotated[str, "Conversation session ID (injected)"],
    user_query: Annotated[str, "Original user query (injected)"],
) -> str:
    """Save an important health insight for future reference.

    Use this internally when discovering significant patterns or insights
    that should be remembered for future conversations.

    Args:
        insight: The key insight to save

    Returns:
        Confirmation of insight being saved
    """
    memory_id = await episodic_memory.save_health_insight(
        session=db_session,
        user_id=user_id,
        session_id=session_id,
        user_query=user_query,
        agent_response=insight,
    )

    if not memory_id:
        return "I noted this insight but couldn't save it to long-term memory."

    return f"I've noted this insight and will remember it for our future conversations."
