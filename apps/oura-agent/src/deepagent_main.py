"""
Oura Health Agent - Deep Agent Version (LangChain deepagents framework)

A hierarchical multi-agent system that answers health questions by routing to
specialized subagents, each responsible for a health data domain.

Subagents:
- sleep_analyst: Sleep periods, stages, quality, trends
- activity_specialist: Daily activity, workouts, movement
- readiness_advisor: Readiness scores, recovery metrics
- heart_health_monitor: Heart rate, HRV, cardiovascular age
- stress_manager: Stress data, mental recovery
- recovery_specialist: Sleep efficiency, respiratory rate, training load
- memory_keeper: Goals, recall, baselines, personal history
- data_auditor: Data freshness, sync status, quality validation

pip install deepagents langchain-anthropic
"""

import asyncio
import logging
import os
from typing import Annotated

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

from database.connection import get_async_session
from database.queries import OuraDataQueries
from database.data_quality import DataQualityValidator, data_validator
from discord.client import DiscordClient
from src.config import get_config, setup_logging
from memory.episodic import EpisodicMemory
from memory.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL DEFINITIONS (used by subagents)
# ============================================================================

class OuraToolFactory:
    """Factory for creating Oura-specific tools with shared state."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.queries = OuraDataQueries(connection_string)
        self.validator = data_validator

    def get_sleep_tools(self):
        """Tools for sleep analysis."""
        queries = self.queries
        validator = self.validator

        @tool
        async def get_last_night_sleep() -> str:
            """Get detailed sleep data from last night including duration, stages, quality score, HRV."""
            data = await queries.get_last_night_sleep()
            validation = validator.validate("oura_sleep_periods", data)

            if not validation.valid:
                return validation.warning

            result = f"""Last Night's Sleep ({validation.latest_date}):
📊 **Overall**
• Sleep Score: {data.get('score', 'N/A')}/100
• Total Sleep: {data.get('total_sleep_hours', 'N/A'):.1f} hours
• Efficiency: {data.get('efficiency_percent', 'N/A'):.0f}%

🌙 **Sleep Stages**
• Deep Sleep: {data.get('deep_hours', 0)*60:.0f} min ({data.get('deep_percentage', 'N/A'):.0f}%)
• REM Sleep: {data.get('rem_hours', 0)*60:.0f} min ({data.get('rem_percentage', 'N/A'):.0f}%)
• Light Sleep: {data.get('light_hours', 0)*60:.0f} min ({data.get('light_percentage', 'N/A'):.0f}%)

❤️ **Physiological**
• Avg HR: {data.get('heart_rate_avg', 'N/A')} bpm
• Lowest HR: {data.get('heart_rate_min', 'N/A')} bpm
• Avg HRV: {data.get('hrv_avg', 'N/A')} ms
• Respiratory Rate: {data.get('respiratory_rate', 'N/A')} breaths/min"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"
            return result

        @tool
        async def get_sleep_trends(days: int = 7) -> str:
            """Get sleep trends over the last N days."""
            df = await queries.get_sleep_trends(days=days)
            return f"Sleep trends for last {days} days:\n{df.to_string()}"

        @tool
        async def get_sleep_quality_detail() -> str:
            """Get detailed sleep quality breakdown for recent nights."""
            scores = await queries.get_daily_sleep_scores(days=7)
            return f"Sleep quality scores (last 7 days):\n{scores.to_string()}"

        return [get_last_night_sleep, get_sleep_trends, get_sleep_quality_detail]

    def get_activity_tools(self):
        """Tools for activity analysis."""
        queries = self.queries

        @tool
        async def get_today_activity() -> str:
            """Get today's activity data: steps, calories, activity score."""
            data = await queries.get_today_activity()
            if not data:
                return "No activity data available yet today."

            return f"""Today's Activity:
🚶 **Movement**
• Steps: {data.get('steps', 'N/A')}
• Distance: {data.get('distance_km', 'N/A'):.2f} km
• Activity Score: {data.get('activity_score', 'N/A')}/100

🔥 **Intensity Breakdown**
• High Activity: {data.get('high_activity_minutes', 0):.0f} min
• Medium Activity: {data.get('medium_activity_minutes', 0):.0f} min
• Low Activity: {data.get('low_activity_minutes', 0):.0f} min
• Sedentary: {data.get('sedentary_minutes', 0):.0f} min

🏋️ **Energy**
• Active Calories: {data.get('calories_active', 'N/A')}
• Total Calories: {data.get('calories_total', 'N/A')}
• MET Minutes: {data.get('met_minutes', 'N/A')}"""

        @tool
        async def get_activity_trends(days: int = 7) -> str:
            """Get activity trends and stats over N days."""
            df = await queries.get_activity_trends(days=days)
            return f"Activity trends (last {days} days):\n{df.to_string()}"

        @tool
        async def get_recent_workouts(days: int = 7) -> str:
            """Get recent workout history."""
            df = await queries.get_recent_workouts(days=days)
            if df.empty:
                return "No recent workouts recorded."
            return f"Recent workouts:\n{df.to_string()}"

        return [get_today_activity, get_activity_trends, get_recent_workouts]

    def get_readiness_tools(self):
        """Tools for readiness and recovery analysis."""
        queries = self.queries
        validator = self.validator

        @tool
        async def get_daily_readiness(days: int = 7) -> str:
            """Get readiness scores and recovery metrics."""
            df = await queries.get_daily_readiness(days=days)
            return f"Readiness scores (last {days} days):\n{df.to_string()}"

        @tool
        async def get_readiness_trends() -> str:
            """Get readiness trends and patterns."""
            df = await queries.get_readiness_trends(days=14)
            return f"14-day readiness trend:\n{df.to_string()}"

        return [get_daily_readiness, get_readiness_trends]

    def get_heart_health_tools(self):
        """Tools for heart rate and HRV analysis."""
        queries = self.queries

        @tool
        async def get_resting_heart_rate(days: int = 7) -> str:
            """Get resting heart rate trends."""
            data = await queries.get_daily_readiness(days=days)
            return f"Resting HR trends (last {days} days):\n{data.to_string()}"

        return [get_resting_heart_rate]

    def get_stress_tools(self):
        """Tools for stress analysis."""
        queries = self.queries

        @tool
        async def get_stress_data(days: int = 7) -> str:
            """Get stress levels and mental recovery patterns."""
            # Placeholder - would query stress table when available
            return f"Stress data for last {days} days: [data not yet integrated]"

        return [get_stress_data]

    def get_recovery_tools(self):
        """Tools for recovery and training load analysis."""
        queries = self.queries

        @tool
        async def get_recovery_metrics() -> str:
            """Get sleep efficiency, training load, and recovery status."""
            data = await queries.get_daily_readiness(days=3)
            return f"Recovery metrics:\n{data.to_string()}"

        return [get_recovery_metrics]


async def build_agent(config) -> any:
    """Build the deep agent with all subagents."""

    # Initialize tools factory
    tool_factory = OuraToolFactory(connection_string=config.database.connection_string)

    # Define subagents
    subagents = [
        {
            "name": "sleep_analyst",
            "description": "Analyzes sleep data: quality, stages, efficiency, trends, optimal bedtime recommendations",
            "system_prompt": """You are a Sleep Analysis Specialist. Analyze the user's Oura sleep data.

Your expertise: sleep duration, stages (deep/REM/light), efficiency, patterns, trends, and sleep quality recommendations.

Always cite specific data points with dates. Interpret sleep scores:
- 85+: Excellent sleep
- 70-84: Good sleep
- 50-69: Fair sleep - consider improvements
- Below 50: Poor sleep

Ground all answers in real data, not assumptions. If data is stale, mention it.""",
            "tools": tool_factory.get_sleep_tools(),
        },
        {
            "name": "activity_specialist",
            "description": "Analyzes daily activity: steps, calories, intensity, workouts, movement patterns",
            "system_prompt": """You are an Activity Specialist. Analyze the user's movement and workout data.

Your expertise: daily steps, active calories, exercise intensity, workout history, movement patterns.

Provide specific numbers with dates. High activity is 250+ min/week at moderate+ intensity.

Ground answers in real activity data from their Oura ring.""",
            "tools": tool_factory.get_activity_tools(),
        },
        {
            "name": "readiness_advisor",
            "description": "Analyzes readiness scores, recovery status, exercise recommendations for today",
            "system_prompt": """You are a Readiness Advisor. Help the user understand their recovery and exercise readiness.

Your expertise: readiness scores (0-100), recovery metrics, whether it's a good day for high-intensity training.

Readiness 85+: Good for high-intensity. 50-84: Moderate activity OK. Below 50: Recovery day recommended.

Cite specific readiness scores and recovery indicators.""",
            "tools": tool_factory.get_readiness_tools(),
        },
        {
            "name": "heart_health_monitor",
            "description": "Monitors cardiovascular health: heart rate, HRV, cardiovascular age, resting HR trends",
            "system_prompt": """You are a Heart Health Monitor. Track the user's cardiovascular metrics.

Your expertise: heart rate variability (HRV), resting heart rate, heart rate trends, cardiovascular age.

Normal HRV: 30-100ms (varies by individual). Declining HRV can indicate stress/fatigue.
Normal RHR: 60-100 bpm. Lower is generally better fitness indicator.

Ground all insights in specific measurements.""",
            "tools": tool_factory.get_heart_health_tools(),
        },
        {
            "name": "stress_manager",
            "description": "Analyzes stress levels, mental recovery, and stress management recommendations",
            "system_prompt": """You are a Stress Management Specialist. Help the user understand stress patterns.

Your expertise: stress detection, mental recovery indicators, stress management recommendations.

High stress + low sleep = recovery priority. Note any stress trends affecting recovery.""",
            "tools": tool_factory.get_stress_tools(),
        },
        {
            "name": "recovery_specialist",
            "description": "Optimizes recovery: training load, sleep debt, recovery days, restoration strategies",
            "system_prompt": """You are a Recovery Specialist. Help optimize the user's recovery.

Your expertise: sleep efficiency, training load, recovery debt, when to take easy days.

Key metric: Sleep Efficiency = Total Sleep / Time in Bed. Aim for 85%+.
High training load + low sleep = overtraining risk.""",
            "tools": tool_factory.get_recovery_tools(),
        },
        {
            "name": "memory_keeper",
            "description": "Manages goals, recalls past advice, tracks personal baselines and progress",
            "system_prompt": """You are a Memory Keeper. Track the user's health goals and personal history.

Your expertise: goal management, recalling past advice, comparing against personal baselines.

When user asks "Remember when...", search past conversations for relevant insights.""",
            "tools": [],  # Memory is built-in to deep agent via memory files
        },
        {
            "name": "data_auditor",
            "description": "Validates data quality, checks sync status, reports freshness and collection issues",
            "system_prompt": """You are a Data Auditor. Ensure data integrity and freshness.

Your expertise: data quality validation, sync status, freshness checks, collection alerts.

Alert if: sleep data >2 days old, activity >1 day old, missing data points.
Be transparent about data limitations.""",
            "tools": [],  # Validation integrated into other tools
        },
    ]

    # Create the deep agent
    agent = create_deep_agent(
        model=ChatAnthropic(
            api_key=config.llm.api_key,
            model="claude-sonnet-4-20250514",
        ),
        subagents=subagents,
        system_prompt="""You are the Master Health Advisor, coordinating specialist subagents.

When the user asks a health question:
1. Route to the appropriate specialist(s) based on their expertise
2. Complex queries may need multiple specialists (e.g., "How's my recovery?" → readiness_advisor + recovery_specialist)
3. Synthesize their insights into one cohesive answer
4. Always cite data and dates
5. Be honest about data limitations

Available specialists: sleep_analyst, activity_specialist, readiness_advisor, heart_health_monitor, stress_manager, recovery_specialist, memory_keeper, data_auditor

Keep responses focused and actionable.""",
        memory=[
            "./memory/SOUL.md",
            "./memory/AGENTS.md",
            "./memory/HEARTBEAT.md",
        ],
        backend=None,  # TODO: Use persistent backend in production
    )

    return agent


async def process_discord_message(agent, message: str, user_id: str, channel_id: str) -> str:
    """Process a Discord message through the agent."""

    try:
        logger.info(f"Processing message from {user_id}: {message[:50]}...")

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": f"oura-{user_id}-{channel_id}"}},
        )

        response = result["messages"][-1].content
        logger.info(f"Generated response: {response[:100]}...")

        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return f"I encountered an error processing your question. Please try again or rephrase."


async def polling_loop(agent, discord_client: DiscordClient, config) -> None:
    """Main polling loop checking for new Discord messages."""

    poll_interval = config.discord.poll_interval
    channel_id = config.discord.health_channel_id
    window_minutes = config.discord.message_window_minutes

    logger.info(
        f"Starting polling loop: channel={channel_id}, "
        f"interval={poll_interval}s, window={window_minutes}min"
    )

    while True:
        try:
            # Fetch recent messages
            messages = await discord_client.fetch_messages(
                channel_id=channel_id,
                limit=20,
            )

            # Filter to new, unprocessed messages
            new_messages = await discord_client.filter_new_messages(
                messages=messages,
                window_minutes=window_minutes,
            )

            # Process each new message
            for message in new_messages:
                response = await process_discord_message(
                    agent=agent,
                    message=message.content,
                    user_id=message.author_id,
                    channel_id=message.channel_id,
                )

                # Send response to Discord
                await discord_client.send_health_response(
                    channel_id=message.channel_id,
                    user_id=message.author_id,
                    response_text=response,
                )

                # Mark as processed
                await discord_client.mark_as_processed(
                    channel_id=message.channel_id,
                    message_id=message.id,
                )

            # Wait for next poll
            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            await asyncio.sleep(5)


async def main():
    """Main entry point."""

    # Load configuration
    config = get_config()
    setup_logging(config.log_level)

    logger.info("Oura Health Agent (Deep Agent) starting...")

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

    # Test Discord connection
    if not await discord_client.test_connection():
        logger.error("Discord connection failed")
        return 1

    # Build the deep agent
    logger.info("Building multi-agent health system...")
    agent = await build_agent(config)
    logger.info("✅ Oura Health Agent initialized")
    logger.info("   Subagents: sleep_analyst, activity_specialist, readiness_advisor, heart_health_monitor, stress_manager, recovery_specialist, memory_keeper, data_auditor")

    # Start polling loop
    try:
        await polling_loop(agent, discord_client, config)
    finally:
        logger.info("Oura Health Agent stopped")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
