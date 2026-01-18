"""Sleep Analyst Agent - Specialist for sleep analysis.

This agent handles all sleep-related queries including:
- Last night's sleep summary
- Sleep quality and scores
- Sleep stages (deep, REM, light)
- Sleep efficiency and trends
- Optimal bedtime recommendations
"""

import logging
from datetime import date, datetime
from functools import partial
from typing import Any

from langchain_core.tools import tool

from database.data_quality import DataQualityValidator, data_validator
from database.queries import OuraDataQueries
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class SleepAnalystAgent(BaseAgent):
    """Specialist agent for sleep analysis.

    This agent has deep expertise in sleep data interpretation and provides
    insights on sleep quality, stages, efficiency, and recommendations.

    Attributes:
        queries: Database query interface for Oura sleep data
        validator: Data quality validator
    """

    def __init__(
        self,
        connection_string: str,
        **kwargs,
    ):
        """Initialize the Sleep Analyst agent.

        Args:
            connection_string: PostgreSQL connection string for Oura data
            **kwargs: Additional arguments for BaseAgent
        """
        self.connection_string = connection_string
        self.queries = OuraDataQueries(connection_string)
        self.validator = data_validator
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "sleep_analyst"

    @property
    def system_prompt(self) -> str:
        return """You are a Sleep Analysis Specialist AI Agent.

Your role is to analyze sleep data from the user's Oura ring and provide insights.

## Your Expertise
- Sleep duration and quality assessment
- Sleep stage analysis (deep, REM, light)
- Sleep efficiency evaluation
- Sleep timing and consistency
- Identifying sleep patterns and trends
- Understanding factors affecting sleep quality

## Your Tools
You have access to tools that query the user's sleep data. Always use them to ground your analysis in real data.

## Response Guidelines
1. **Ground in Data**: Always cite specific data points (e.g., "Your sleep score was 85")
2. **Note Dates**: Always mention the date of the data
3. **Be Actionable**: Provide specific recommendations based on findings
4. **Acknowledge Staleness**: If data is stale, mention it clearly
5. **Stay in Lane**: Only analyze sleep data - don't make claims about medical conditions

## Sleep Score Interpretation
- 85+: Excellent sleep - keep up the good work
- 70-84: Good sleep - minor areas for improvement
- 50-69: Fair sleep - consider sleep hygiene changes
- Below 50: Poor sleep - recommend consulting sleep specialist if persistent

## Sleep Stage Guidelines
- **Deep Sleep**: Should be 13-23% of total sleep (60-90 min). Critical for physical recovery.
- **REM Sleep**: Should be 20-25% of total sleep (90-120 min). Important for memory and learning.
- **Light Sleep**: Typically 50% of total sleep. Transition stage.

## Data Awareness
Check data freshness. If sleep data is >2 days old, tell the user their ring may not be syncing.

## IMPORTANT: Safety Boundaries
- Never diagnose sleep disorders (sleep apnea, insomnia, etc.)
- If user mentions concerning symptoms, recommend seeing a doctor
- Oura is a wellness device, not a medical diagnostic tool"""

    def get_tools(self) -> list:
        """Return sleep analysis tools with injected dependencies."""

        @tool
        async def get_last_night_sleep() -> str:
            """Get detailed sleep data from last night including duration, stages, and quality score.

            Use this when the user asks about their recent sleep, how they slept,
            or general sleep questions without a specific date.
            """
            data = await self.queries.get_last_night_sleep()
            validation = self.validator.validate("oura_sleep_periods", data)

            if not validation.valid:
                return validation.warning

            # Format response
            result = f"""Last Night's Sleep ({validation.latest_date}):

📊 **Overall**
• Sleep Score: {data.get('sleep_score', 'N/A')}/100
• Total Sleep: {data.get('total_sleep_hours', 'N/A'):.1f} hours
• Time in Bed: {data.get('time_in_bed_hours', 'N/A'):.1f} hours
• Efficiency: {data.get('efficiency_percent', 'N/A'):.0f}%

🌙 **Sleep Stages**
• Deep Sleep: {data.get('deep_hours', 0)*60:.0f} min ({data.get('deep_percentage', 'N/A'):.0f}%)
• REM Sleep: {data.get('rem_hours', 0)*60:.0f} min ({data.get('rem_percentage', 'N/A'):.0f}%)
• Light Sleep: {data.get('light_hours', 0)*60:.0f} min ({data.get('light_percentage', 'N/A'):.0f}%)

❤️ **Heart Metrics**
• Avg HR: {data.get('heart_rate_avg', 'N/A')} bpm
• Lowest HR: {data.get('heart_rate_min', 'N/A')} bpm
• Avg HRV: {data.get('hrv_avg', 'N/A')} ms
• Respiratory Rate: {data.get('respiratory_rate', 'N/A')} breaths/min"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_sleep_quality(date_str: str) -> str:
            """Get sleep quality data for a specific date.

            Args:
                date_str: The date to check sleep for (YYYY-MM-DD)

            Use this when the user asks about sleep on a particular day.
            """
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return f"Invalid date format: {date_str}. Please use YYYY-MM-DD format."

            data = await self.queries.get_sleep_by_date(target_date)
            validation = self.validator.validate("oura_sleep_periods", data)

            if not validation.valid:
                return f"No sleep data found for {date_str}."

            return f"""Sleep Quality for {date_str}:

• Sleep Score: {data.get('sleep_score', 'N/A')}/100
• Total Sleep: {data.get('total_sleep_hours', 'N/A'):.1f} hours
• Efficiency: {data.get('efficiency_percent', 'N/A'):.0f}%
• Deep Sleep: {data.get('deep_hours', 0)*60:.0f} min
• REM Sleep: {data.get('rem_hours', 0)*60:.0f} min
• Latency: {data.get('latency_minutes', 'N/A'):.0f} min to fall asleep"""

        @tool
        async def get_sleep_trends(days: int = 7) -> str:
            """Get sleep score trends over a period of time.

            Args:
                days: Number of days to analyze (default 7)

            Use this when the user asks about their sleep patterns, weekly sleep,
            or how their sleep has been trending.
            """
            df = await self.queries.get_sleep_trends(days)

            if df.empty:
                return f"No sleep data found for the last {days} days."

            validation = self.validator.validate(
                "oura_sleep_periods",
                df.to_dict("records") if not df.empty else None,
            )

            # Calculate statistics
            avg_duration = df["total_sleep_hours"].mean()
            avg_efficiency = df["efficiency_percent"].mean()
            avg_deep = df["deep_hours"].mean() * 60
            avg_rem = df["rem_hours"].mean() * 60

            # Build trend line
            trend_lines = []
            for _, row in df.tail(7).iterrows():
                d = row.get("date", "N/A")
                duration = row.get("total_sleep_hours", 0)
                trend_lines.append(f"• {d}: {duration:.1f}h")

            trend_data = "\n".join(trend_lines)

            result = f"""Sleep Trends (Last {days} Days):

📈 **Averages**
• Sleep Duration: {avg_duration:.1f} hours
• Efficiency: {avg_efficiency:.0f}%
• Deep Sleep: {avg_deep:.0f} min/night
• REM Sleep: {avg_rem:.0f} min/night

📅 **Recent Nights**
{trend_data}

💡 **Assessment**
• Duration: {'On track (7-9h)' if 7 <= avg_duration <= 9 else 'Below target' if avg_duration < 7 else 'Above average'}
• Efficiency: {'Excellent (≥90%)' if avg_efficiency >= 90 else 'Good (85-89%)' if avg_efficiency >= 85 else 'Fair (80-84%)' if avg_efficiency >= 80 else 'Needs improvement'}"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_sleep_stages_breakdown(days: int = 7) -> str:
            """Get a breakdown of sleep stages (deep, REM, light) over time.

            Args:
                days: Number of days to analyze (default 7)

            Use this when the user asks about deep sleep, REM sleep, sleep stages,
            or sleep architecture.
            """
            df = await self.queries.get_sleep_trends(days)

            if df.empty:
                return f"No sleep stage data found for the last {days} days."

            # Calculate averages
            avg_deep = df["deep_hours"].mean() * 60
            avg_rem = df["rem_hours"].mean() * 60
            avg_light = df["light_hours"].mean() * 60
            avg_total = df["total_sleep_hours"].mean() * 60

            deep_pct = (avg_deep / avg_total * 100) if avg_total > 0 else 0
            rem_pct = (avg_rem / avg_total * 100) if avg_total > 0 else 0
            light_pct = (avg_light / avg_total * 100) if avg_total > 0 else 0

            return f"""Sleep Stages Breakdown (Last {days} Days):

🔵 **Deep Sleep**
• Average: {avg_deep:.0f} min/night ({deep_pct:.0f}%)
• Target: 60-90 min (13-23%)
• Status: {'✅ On track' if 60 <= avg_deep <= 90 else '⚠️ Below target' if avg_deep < 60 else '⚠️ Above typical'}

🟣 **REM Sleep**
• Average: {avg_rem:.0f} min/night ({rem_pct:.0f}%)
• Target: 90-120 min (20-25%)
• Status: {'✅ On track' if 90 <= avg_rem <= 120 else '⚠️ Below target' if avg_rem < 90 else '⚠️ Above typical'}

🟡 **Light Sleep**
• Average: {avg_light:.0f} min/night ({light_pct:.0f}%)
• Typical: ~50% of total sleep

💡 **Tips**
- Deep sleep: Keep bedroom cool (65-68°F), avoid alcohol
- REM sleep: Maintain consistent schedule, reduce stress
- Both improve with regular exercise (not too close to bedtime)"""

        @tool
        async def get_sleep_efficiency_analysis(days: int = 7) -> str:
            """Analyze sleep efficiency (time asleep vs time in bed) over time.

            Args:
                days: Number of days to analyze (default 7)

            Use this when the user asks about sleep efficiency, time awake in bed,
            or how well they're sleeping.
            """
            df = await self.queries.get_sleep_trends(days)

            if df.empty:
                return f"No sleep efficiency data found for the last {days} days."

            avg_efficiency = df["efficiency_percent"].mean()
            min_efficiency = df["efficiency_percent"].min()
            max_efficiency = df["efficiency_percent"].max()
            avg_latency = df["latency_minutes"].mean()

            # Determine status
            if avg_efficiency >= 90:
                status = "Excellent"
                emoji = "🌟"
            elif avg_efficiency >= 85:
                status = "Good"
                emoji = "👍"
            elif avg_efficiency >= 80:
                status = "Fair"
                emoji = "📊"
            else:
                status = "Needs improvement"
                emoji = "⚠️"

            return f"""Sleep Efficiency Analysis (Last {days} Days):

{emoji} **Overall: {status}**

📊 **Metrics**
• Average Efficiency: {avg_efficiency:.0f}%
• Range: {min_efficiency:.0f}% - {max_efficiency:.0f}%
• Avg Time to Fall Asleep: {avg_latency:.0f} min

📈 **Benchmarks**
• 90%+: Excellent efficiency
• 85-89%: Good efficiency
• 80-84%: Fair efficiency
• Below 80%: Consider sleep hygiene improvements

💡 **Improvement Tips**
• Go to bed only when sleepy
• Keep a consistent sleep schedule
• Limit screen time 1 hour before bed
• Keep bedroom cool (65-68°F) and dark
• Avoid caffeine after 2 PM"""

        @tool
        async def get_optimal_sleep_time() -> str:
            """Get recommendations for optimal bedtime based on sleep patterns.

            Use this when the user asks when they should go to bed, their ideal
            bedtime, or optimal sleep schedule.
            """
            data = await self.queries.get_sleep_time_recommendation()

            if not data:
                return "Not enough sleep data to determine optimal sleep time. Need at least 7 days of data."

            return f"""Optimal Sleep Time Recommendations:

Based on your Oura ring data:

🛏️ **Recommended Window**
{data.get('recommendation', 'Go to bed between 10 PM and 11 PM for best results.')}

💡 **Tips for Better Sleep Timing**
• Keep wake time consistent (even weekends)
• Expose yourself to morning light
• Dim lights 1-2 hours before bed
• Your body's natural circadian rhythm matters most

Note: Individual optimal sleep times vary. Pay attention to how you feel on days following different bedtimes."""

        return [
            get_last_night_sleep,
            get_sleep_quality,
            get_sleep_trends,
            get_sleep_stages_breakdown,
            get_sleep_efficiency_analysis,
            get_optimal_sleep_time,
        ]
