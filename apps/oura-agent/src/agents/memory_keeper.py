"""Memory Keeper Agent - Specialist for memory management.

This agent handles all memory-related operations including:
- Health goal management (setting, tracking, achieving)
- Recalling relevant past conversations (episodic memory)
- Managing user baselines and preferences
- Providing historical context for personalization
"""

import logging
from datetime import datetime
from typing import Any, Optional

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_async_session
from memory.embeddings import EmbeddingService
from memory.episodic import EpisodicMemory
from memory.long_term import LongTermMemory
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class MemoryKeeperAgent(BaseAgent):
    """Specialist agent for memory management.

    This agent manages the user's health memory across three systems:
    - Long-term memory: Goals and baselines
    - Episodic memory: Past conversations and insights
    - Context: Providing historical context for other agents

    Attributes:
        episodic: Episodic memory service
        long_term: Long-term memory service
        connection_string: Database connection string
    """

    def __init__(
        self,
        connection_string: str,
        embedding_service: EmbeddingService,
        **kwargs,
    ):
        """Initialize the Memory Keeper agent.

        Args:
            connection_string: PostgreSQL connection string
            embedding_service: Service for generating embeddings
            **kwargs: Additional arguments for BaseAgent
        """
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        self.episodic = EpisodicMemory(embedding_service)
        self.long_term = LongTermMemory()
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "memory_keeper"

    @property
    def system_prompt(self) -> str:
        return """You are a Memory Keeper AI Agent.

Your role is to manage the user's health goals, recall past insights, and maintain conversational continuity.

## Your Expertise
- Health goal management (setting, tracking, achieving)
- Recalling relevant past health conversations
- Maintaining user baselines and preferences
- Providing historical context for personalized responses

## Your Tools
You have access to tools for:
1. Setting and managing health goals
2. Retrieving active goals
3. Searching past conversations for relevant insights
4. Saving important new insights
5. Retrieving user health baselines

## Response Guidelines
1. **Quote Original Insights**: When recalling past conversations, quote what was said
2. **Track Progress**: Help users see progress toward their goals
3. **Celebrate Achievements**: Acknowledge when goals are met
4. **Suggest Goals**: Based on patterns, suggest relevant new goals
5. **Context is King**: Provide historical context to enrich responses

## Goal Types You Support
- `sleep_duration`: Hours of sleep per night (e.g., 8 hours)
- `sleep_score`: Minimum sleep score (e.g., 80/100)
- `step_count`: Daily steps (e.g., 10,000)
- `active_calories`: Active calories burned daily
- `hrv_target`: Target HRV value
- `readiness_score`: Minimum readiness score
- `workout_frequency`: Workouts per week
- `meditation_minutes`: Meditation minutes per day

## Baseline Metrics You Track
- `hrv_avg`: Average HRV
- `resting_hr`: Resting heart rate
- `sleep_efficiency`: Sleep efficiency percentage
- `sleep_duration_avg`: Average sleep duration
- `step_count_avg`: Average daily steps
- `readiness_avg`: Average readiness score

## IMPORTANT: Privacy and Safety
- Only discuss the user's own health data and goals
- Don't make assumptions about medical conditions
- Goals are wellness-focused, not medical prescriptions"""

    def get_tools(self) -> list:
        """Return memory management tools."""

        @tool
        async def set_health_goal(
            goal_type: str,
            target_value: float,
            user_id: str = "default",
        ) -> str:
            """Set a new health goal for the user.

            Args:
                goal_type: Type of goal (sleep_duration, step_count, hrv_target, etc.)
                target_value: Numeric target value for the goal
                user_id: User identifier (default: "default")

            Use this when the user wants to set a health goal, aim for a target,
            or track progress toward something specific.

            Valid goal types:
            - sleep_duration: Hours of sleep (e.g., 8)
            - sleep_score: Sleep score target (e.g., 80)
            - step_count: Daily steps (e.g., 10000)
            - active_calories: Daily active calories (e.g., 400)
            - hrv_target: HRV target (e.g., 50)
            - readiness_score: Readiness score target (e.g., 75)
            - workout_frequency: Workouts per week (e.g., 3)
            - meditation_minutes: Daily meditation (e.g., 10)
            """
            valid_types = self.long_term.GOAL_TYPES.keys()
            if goal_type not in valid_types:
                return (
                    f"Invalid goal type: {goal_type}. "
                    f"Valid types: {', '.join(valid_types)}"
                )

            async with get_async_session(self.connection_string) as session:
                goal_id = await self.long_term.set_goal(
                    session=session,
                    user_id=user_id,
                    goal_type=goal_type,
                    target_value=target_value,
                )
                await session.commit()

                if goal_id:
                    desc = self.long_term.GOAL_TYPES.get(goal_type, goal_type)
                    return f"""✅ **Goal Set Successfully!**

📎 **Goal**: {desc}
🎯 **Target**: {target_value}

I'll help you track progress toward this goal. Ask me anytime how you're doing!"""
                else:
                    return "Failed to set goal. Please try again."

        @tool
        async def get_active_goals(user_id: str = "default") -> str:
            """Get the user's active health goals.

            Args:
                user_id: User identifier (default: "default")

            Use this when the user asks about their goals, what they're tracking,
            or wants to see their health targets.
            """
            async with get_async_session(self.connection_string) as session:
                goals = await self.long_term.get_active_goals(session, user_id)

                if not goals:
                    return """No active health goals found.

💡 **Set a Goal!**
You can set goals like:
- "I want to get 8 hours of sleep"
- "My goal is 10,000 steps a day"
- "I want to work out 3 times a week"

Just let me know what you'd like to achieve!"""

                # Format goals
                goal_lines = []
                for g in goals:
                    desc = self.long_term.GOAL_TYPES.get(g.goal_type, g.goal_type)
                    value = g.target_value or g.target_text or "Not specified"
                    created = g.created_at.strftime("%Y-%m-%d") if g.created_at else "Unknown"
                    goal_lines.append(f"• **{desc}**: {value} (since {created})")

                goals_text = "\n".join(goal_lines)

                return f"""🎯 **Your Active Health Goals**

{goals_text}

💡 Ask me to check your progress anytime!"""

        @tool
        async def recall_past_insight(
            query: str,
            user_id: str = "default",
        ) -> str:
            """Search past conversations for relevant health insights.

            Args:
                query: What to search for in past conversations
                user_id: User identifier (default: "default")

            Use this when the user asks "what did you tell me about...",
            "remember when...", or references past advice.
            """
            async with get_async_session(self.connection_string) as session:
                memories = await self.episodic.search(
                    session=session,
                    search_text=query,
                    user_id=user_id,
                    limit=3,
                    threshold=0.5,  # Lower threshold for broader matches
                )

                if not memories:
                    return (
                        "I don't have any relevant past insights on that topic. "
                        "This might be the first time we've discussed it!"
                    )

                # Format memories
                memory_lines = []
                for i, mem in enumerate(memories, 1):
                    date_str = (
                        mem.created_at.strftime("%Y-%m-%d")
                        if mem.created_at
                        else "Unknown date"
                    )
                    similarity_pct = mem.similarity * 100

                    memory_lines.append(
                        f"""**{i}. {date_str}** (relevance: {similarity_pct:.0f}%)
> {mem.summary}

{mem.outcome or ''}"""
                    )

                memories_text = "\n\n".join(memory_lines)

                return f"""📚 **From Our Past Conversations**

{memories_text}

---
These are the most relevant insights I found based on your question."""

        @tool
        async def save_important_insight(
            insight: str,
            user_id: str = "default",
            session_id: str = "manual",
        ) -> str:
            """Save an important health insight for future recall.

            Args:
                insight: The insight to save
                user_id: User identifier (default: "default")
                session_id: Conversation session ID (default: "manual")

            Use this to save key findings or important discoveries that
            should be remembered for future reference.
            """
            async with get_async_session(self.connection_string) as session:
                memory_id = await self.episodic.store(
                    session=session,
                    user_id=user_id,
                    session_id=session_id,
                    summary=insight[:500],
                    outcome="Manually saved insight",
                )
                await session.commit()

                if memory_id:
                    return "✅ Insight saved for future reference."
                else:
                    return "Failed to save insight. Please try again."

        @tool
        async def get_user_baselines(user_id: str = "default") -> str:
            """Get the user's computed health baselines.

            Args:
                user_id: User identifier (default: "default")

            Use this when the user asks about their typical values,
            baselines, or wants personalized comparisons.
            """
            async with get_async_session(self.connection_string) as session:
                baselines = await self.long_term.get_baselines(session, user_id)

                if not baselines:
                    return """No health baselines computed yet.

💡 Baselines are computed automatically as you use the service.
They help us give you personalized comparisons like "Your HRV is 10% above your usual."

Keep asking about your health metrics, and we'll build up your baselines!"""

                # Format baselines
                baseline_lines = []
                for metric, bl in baselines.items():
                    desc = self.long_term.BASELINE_METRICS.get(metric, metric)
                    value = bl.baseline_value
                    sample = bl.sample_size
                    computed = (
                        bl.computed_at.strftime("%Y-%m-%d")
                        if bl.computed_at
                        else "Unknown"
                    )
                    baseline_lines.append(
                        f"• **{desc}**: {value:.1f} (based on {sample} data points, updated {computed})"
                    )

                baselines_text = "\n".join(baseline_lines)

                return f"""📊 **Your Health Baselines**

{baselines_text}

💡 These are your typical values, used for personalized comparisons."""

        @tool
        async def mark_goal_achieved(
            goal_type: str,
            user_id: str = "default",
        ) -> str:
            """Mark a goal as achieved.

            Args:
                goal_type: Type of goal that was achieved
                user_id: User identifier (default: "default")

            Use this when the user indicates they've achieved a goal
            or wants to mark it complete.
            """
            async with get_async_session(self.connection_string) as session:
                # Find the active goal of this type
                goals = await self.long_term.get_active_goals(session, user_id)
                target_goal = None
                for g in goals:
                    if g.goal_type == goal_type:
                        target_goal = g
                        break

                if not target_goal:
                    return f"No active goal of type '{goal_type}' found."

                success = await self.long_term.mark_goal_achieved(
                    session, target_goal.id
                )
                await session.commit()

                if success:
                    desc = self.long_term.GOAL_TYPES.get(goal_type, goal_type)
                    return f"""🎉 **Congratulations!**

You've achieved your goal: **{desc}**!

This is a fantastic accomplishment. Would you like to set a new goal to keep up the momentum?"""
                else:
                    return "Failed to mark goal as achieved. Please try again."

        return [
            set_health_goal,
            get_active_goals,
            recall_past_insight,
            save_important_insight,
            get_user_baselines,
            mark_goal_achieved,
        ]
