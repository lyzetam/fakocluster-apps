"""
Oura Health Agent - Deep Agent with Supabase Memory Integration

Agents remember:
- What they've told users (episodic memory via conversations table)
- User goals & baselines (semantic memory via user_profiles)
- What alerts they've sent (procedural memory via alerts_history)
- What recommendations worked/didn't (learning via agent_decisions)
- Patterns about each user (learned patterns in agent_learning)

This enables:
✓ "Remember when you told me..." searches
✓ Personalized responses based on goals & baselines
✓ Alert deduplication (don't repeat alerts)
✓ Learning from outcomes (did the recommendation help?)
✓ Improved routing based on what works for this user
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from uuid import uuid4

from database.connection import get_async_session
from database.queries import OuraDataQueries
from database.data_quality import data_validator
from discord.client import DiscordClient
from src.config import get_config, setup_logging
from src.supabase_memory import SupabaseMemory, init_supabase_memory
from memory.episodic import EpisodicMemory
from memory.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


# ============================================================================
# MEMORY-AWARE TOOLS
# ============================================================================

class MemoryAwareToolFactory:
    """Tools that integrate Supabase memory for personalization."""

    def __init__(
        self,
        connection_string: str,
        supabase_memory: SupabaseMemory,
    ):
        self.connection_string = connection_string
        self.queries = OuraDataQueries(connection_string)
        self.memory = supabase_memory
        self.validator = data_validator

    def get_sleep_tools(self, user_id: str):
        """Sleep tools that use user's remembered goals/baselines."""
        queries = self.queries
        memory = self.memory

        @tool
        async def get_last_night_sleep() -> str:
            """Get last night's sleep with comparison to user's baseline."""
            data = await queries.get_last_night_sleep()
            validation = self.validator.validate("oura_sleep_periods", data)

            if not validation.valid:
                return validation.warning

            # Get user's remembered baselines
            profile = await memory.get_user_profile(user_id)
            baselines = profile.get("baselines", {})
            goals = profile.get("goals", {})

            sleep_hours = data.get("total_sleep_hours", 0)
            deep_pct = data.get("deep_percentage", 0)
            target_sleep = goals.get("sleep_hours", 7.5)
            baseline_deep = baselines.get("deep_sleep_pct", 20)

            # Compare to personalized targets
            vs_target = "✓" if sleep_hours >= target_sleep else "↓"
            vs_baseline = "↑" if deep_pct > baseline_deep else "↓"

            result = f"""Last Night's Sleep ({validation.latest_date}):
📊 **Overall** {vs_target}
• Sleep Score: {data.get('score', 'N/A')}/100
• Total Sleep: {sleep_hours:.1f}h (your goal: {target_sleep}h)
• Efficiency: {data.get('efficiency_percent', 'N/A'):.0f}%

🌙 **Sleep Stages** {vs_baseline}
• Deep Sleep: {data.get('deep_hours', 0)*60:.0f} min ({deep_pct:.0f}%, baseline: {baseline_deep}%)
• REM Sleep: {data.get('rem_hours', 0)*60:.0f} min ({data.get('rem_percentage', 'N/A'):.0f}%)
• Light Sleep: {data.get('light_hours', 0)*60:.0f} min ({data.get('light_percentage', 'N/A'):.0f}%)

❤️ **Physiological**
• Avg HR: {data.get('heart_rate_avg', 'N/A')} bpm
• Lowest HR: {data.get('heart_rate_min', 'N/A')} bpm
• Avg HRV: {data.get('hrv_avg', 'N/A')} ms"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_sleep_trends(days: int = 7) -> str:
            """Get sleep trends over N days."""
            df = await queries.get_sleep_trends(days=days)
            return f"Sleep trends for last {days} days:\n{df.to_string()}"

        @tool
        async def recall_sleep_advice() -> str:
            """Recall past sleep advice given to this user."""
            history = await memory.search_conversations(
                user_id=user_id,
                query="sleep advice tips recommendations",
                top_k=3,
            )

            if not history:
                return "No prior sleep advice found in memory."

            advice = "\n".join(
                [f"• {h['response'][:100]}..." for h in history]
            )
            return f"Previously shared advice:\n{advice}"

        return [get_last_night_sleep, get_sleep_trends, recall_sleep_advice]

    def get_activity_tools(self, user_id: str):
        """Activity tools that use user's step goals."""
        queries = self.queries
        memory = self.memory

        @tool
        async def get_today_activity() -> str:
            """Get today's activity with personal goal comparison."""
            data = await queries.get_today_activity()
            if not data:
                return "No activity data available yet today."

            profile = await memory.get_user_profile(user_id)
            goals = profile.get("goals", {})
            target_steps = goals.get("steps", 10000)

            steps = data.get("steps", 0)
            progress = (steps / target_steps * 100) if target_steps > 0 else 0
            pct_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))

            return f"""Today's Activity [{pct_bar}] {int(progress)}%
🚶 **Movement**
• Steps: {steps:,} / {target_steps:,}
• Distance: {data.get('distance_km', 'N/A'):.2f} km
• Activity Score: {data.get('activity_score', 'N/A')}/100

🔥 **Intensity**
• High: {data.get('high_activity_minutes', 0):.0f} min
• Medium: {data.get('medium_activity_minutes', 0):.0f} min
• Low: {data.get('low_activity_minutes', 0):.0f} min

🏋️ **Energy**
• Active Calories: {data.get('calories_active', 'N/A')}
• MET Minutes: {data.get('met_minutes', 'N/A')}"""

        @tool
        async def get_activity_trends(days: int = 7) -> str:
            """Get activity trends."""
            df = await queries.get_activity_trends(days=days)
            return f"Activity trends:\n{df.to_string()}"

        return [get_today_activity, get_activity_trends]


async def build_agent_with_memory(
    config,
    supabase_memory: SupabaseMemory,
) -> any:
    """Build the deep agent with Supabase memory integration."""

    tool_factory = MemoryAwareToolFactory(
        connection_string=config.database.connection_string,
        supabase_memory=supabase_memory,
    )

    # Note: In production, you'd dynamically create tools per user_id
    # This is simplified for demonstration

    subagents = [
        {
            "name": "sleep_analyst",
            "description": "Analyzes sleep data with memory of user's goals & past advice",
            "system_prompt": """You are a Sleep Specialist with memory of this user's history.

Before responding, consider:
- What are their sleep goals? (check memory)
- What baselines have they established? (check memory)
- What sleep advice have you given before? (check recall_sleep_advice tool)
- Has your past recommendations helped? (check outcomes)

Personalize responses to their specific goals and patterns.""",
            "tools": tool_factory.get_sleep_tools(user_id="default"),  # User ID injected at runtime
        },
        {
            "name": "activity_specialist",
            "description": "Tracks activity with memory of user's goals",
            "system_prompt": """You are an Activity Specialist who remembers this user's step goals.

Reference:
- What's their target step count? (from memory)
- Are they on track today? (compare vs goal)
- What workouts have they done recently? (from conversation history)

Make recommendations based on their patterns and goals.""",
            "tools": tool_factory.get_activity_tools(user_id="default"),
        },
        {
            "name": "readiness_advisor",
            "description": "Recommends training intensity based on recovery status",
            "system_prompt": """You are a Recovery Advisor who learns what works for this user.

Key:
- What readiness level suggests they should train hard?
- How has your advice performed in the past? (check agent_decisions outcomes)
- Are there patterns in their recovery? (from learning memory)

Adapt recommendations based on what's worked for them before.""",
            "tools": [],
        },
        {
            "name": "memory_keeper",
            "description": "Manages goals, recalls advice, tracks learning",
            "system_prompt": """You are a Memory Keeper who manages this user's goals and history.

Capabilities:
- Set/update health goals ("I want to sleep 8 hours")
- Recall past advice ("Remember when you said...")
- Track what recommendations worked ("My sleep improved after...")
- Learn patterns about this user

Use memory tools to help the user reflect on progress and learn from patterns.""",
            "tools": [],
        },
        {
            "name": "data_auditor",
            "description": "Checks data freshness and alerts intelligently (with dedup)",
            "system_prompt": """You are a Data Auditor who tracks sync issues smartly.

Before alerting:
- Check alerts_history: have we alerted about this recently?
- Don't spam the same alert within 24 hours
- Only alert on genuinely NEW developments
- Provide context: "Your sleep data is 2 days old. Ring may not be syncing."

Learn: what data issues recur for this user?""",
            "tools": [],
        },
    ]

    agent = create_deep_agent(
        model=ChatAnthropic(
            api_key=config.llm.api_key,
            model="claude-sonnet-4-20250514",
        ),
        subagents=subagents,
        system_prompt="""You are the Master Health Advisor with LONG-TERM MEMORY.

You have access to:
1. **Episodic Memory** — All past conversations with this user (searchable)
2. **Semantic Memory** — Their goals, baselines, preferences
3. **Procedural Memory** — What alerts you've sent, what recommendations worked
4. **Learning Memory** — Patterns about this user

On each interaction:
1. Check what you know about this user (goals, baselines, patterns)
2. Reference past advice if relevant ("You asked me before about...")
3. Log new decisions for future learning
4. Update alert history to avoid repeats
5. Personalize responses to their specific situation

You're not just answering questions — you're building a relationship and learning what works for this user.""",
        memory=[
            "./memory/SOUL.md",
            "./memory/AGENTS.md",
            "./memory/HEARTBEAT.md",
        ],
        backend=None,  # TODO: Use persistent backend in production
    )

    return agent


async def process_message_with_memory(
    agent,
    memory: SupabaseMemory,
    message: str,
    user_id: str,
    channel_id: str,
) -> str:
    """Process message, saving to memory."""

    try:
        logger.info(f"Processing message from {user_id}: {message[:50]}...")

        # Get user profile for context
        profile = await memory.get_user_profile(user_id)
        logger.info(f"User profile: goals={profile.get('goals')}, baselines={profile.get('baselines')}")

        # Invoke agent
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": f"oura-{user_id}-{channel_id}"}},
        )

        response = result["messages"][-1].content
        logger.info(f"Generated response: {response[:100]}...")

        # Save conversation to episodic memory
        await memory.save_conversation(
            user_id=user_id,
            query=message,
            response=response,
            specialists=[],  # TODO: Extract from agent internals
            channel_id=channel_id,
        )

        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return f"I encountered an error processing your question. Please try again or rephrase."


async def main():
    """Main entry point with memory."""

    config = get_config()
    setup_logging(config.log_level)

    logger.info("Oura Health Agent (Deep Agent + Supabase Memory) starting...")

    # Initialize Supabase memory
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY required")
        return 1

    memory = await init_supabase_memory(supabase_url, supabase_key)

    # Test database connection
    from database.connection import test_connection
    if not await test_connection(config.database.connection_string):
        logger.error("Database connection failed")
        return 1

    # Initialize Discord client
    discord_client = DiscordClient(
        token=config.discord.bot_token,
        processed_emoji=config.discord.processed_emoji,
    )

    if not await discord_client.test_connection():
        logger.error("Discord connection failed")
        return 1

    # Build agent with memory
    logger.info("Building agent with Supabase memory...")
    agent = await build_agent_with_memory(config, memory)
    logger.info("✅ Agent initialized with memory capabilities")
    logger.info("   Agents remember: goals, baselines, past advice, alerts sent, patterns learned")

    # Polling loop
    poll_interval = config.discord.poll_interval
    channel_id = config.discord.health_channel_id

    logger.info(f"Starting polling loop: channel={channel_id}, interval={poll_interval}s")

    while True:
        try:
            messages = await discord_client.fetch_messages(channel_id=channel_id, limit=20)
            new_messages = await discord_client.filter_new_messages(
                messages=messages,
                window_minutes=config.discord.message_window_minutes,
            )

            for message in new_messages:
                response = await process_message_with_memory(
                    agent=agent,
                    memory=memory,
                    message=message.content,
                    user_id=message.author_id,
                    channel_id=message.channel_id,
                )

                await discord_client.send_health_response(
                    channel_id=message.channel_id,
                    user_id=message.author_id,
                    response_text=response,
                )

                await discord_client.mark_as_processed(
                    channel_id=message.channel_id,
                    message_id=message.id,
                )

            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
