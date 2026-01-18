"""Fitness Coach Agent - Specialist for activity and readiness.

This agent handles all fitness-related queries including:
- Daily activity (steps, calories, movement)
- Exercise readiness assessment
- Workout tracking and analysis
- Recovery status and recommendations
- HRV and resting heart rate trends
"""

import logging
from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool

from database.data_quality import data_validator
from database.queries import OuraDataQueries
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class FitnessCoachAgent(BaseAgent):
    """Specialist agent for fitness coaching and activity analysis.

    This agent has expertise in activity data, readiness assessment,
    workout tracking, and recovery recommendations.

    Attributes:
        queries: Database query interface for Oura activity data
        validator: Data quality validator
    """

    def __init__(
        self,
        connection_string: str,
        **kwargs,
    ):
        """Initialize the Fitness Coach agent.

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
        return "fitness_coach"

    @property
    def system_prompt(self) -> str:
        return """You are a Fitness Coach AI Agent.

Your role is to analyze activity and readiness data to help the user optimize their fitness.

## Your Expertise
- Activity level assessment (steps, calories, movement)
- Exercise readiness evaluation
- Recovery status monitoring
- Workout tracking and analysis
- HRV and resting heart rate interpretation
- Training load management

## Your Tools
You have access to tools that query the user's activity and readiness data. Always use them to ground your recommendations in real data.

## Response Guidelines
1. **Be Encouraging**: Celebrate achievements and progress
2. **Be Data-Driven**: Base recommendations on actual metrics
3. **Be Practical**: Give specific, actionable advice
4. **Respect Recovery**: If readiness is low, prioritize rest over pushing through

## Readiness Score Interpretation
- 85+: Excellent - Great day for high-intensity training
- 70-84: Good - Moderate exercise recommended
- 50-69: Fair - Light activity or active recovery
- Below 50: Rest day strongly recommended

## Activity Guidelines
- **10,000 steps**: General daily target
- **150 min/week**: WHO moderate activity recommendation
- **75 min/week**: WHO vigorous activity recommendation
- **MET minutes**: 500-1000/week for substantial health benefits

## Training Load Principles
- Allow recovery between intense workouts
- Balance high/medium/low intensity
- Watch for signs of overtraining (elevated RHR, low HRV)
- Progressive overload should be gradual

## IMPORTANT: Safety Boundaries
- Never provide medical advice
- Don't recommend pushing through pain or injury
- Suggest consulting a professional for persistent issues
- Consider the user's individual fitness level"""

    def get_tools(self) -> list:
        """Return fitness coaching tools with injected dependencies."""

        @tool
        async def get_today_activity() -> str:
            """Get today's activity data including steps, calories, and movement.

            Use this when the user asks about today's activity, steps, or how active they were.
            """
            data = await self.queries.get_today_activity()
            validation = self.validator.validate("oura_activity", data)

            if not validation.valid:
                return validation.warning

            # Format response
            steps = data.get("steps", 0)
            step_goal = 10000
            step_pct = (steps / step_goal * 100) if step_goal > 0 else 0

            result = f"""Today's Activity ({validation.latest_date}):

🏃 **Movement**
• Steps: {steps:,} ({step_pct:.0f}% of 10k goal)
• Distance: {data.get('distance_km', 0):.1f} km

🔥 **Calories**
• Total: {data.get('calories_total', 0):,} kcal
• Active: {data.get('calories_active', 0):,} kcal

⏱️ **Activity Time**
• High Intensity: {data.get('high_activity_minutes', 0)} min
• Medium Intensity: {data.get('medium_activity_minutes', 0)} min
• Low Intensity: {data.get('low_activity_minutes', 0)} min
• Sedentary: {data.get('sedentary_minutes', 0)} min

📊 **Score**
• Activity Score: {data.get('activity_score', 'N/A')}/100
• MET Minutes: {data.get('met_minutes', 0)}"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def check_exercise_readiness() -> str:
            """Check if user is ready for exercise based on recovery status.

            Use this when the user asks if they should work out, exercise readiness, or recovery status.
            """
            data = await self.queries.get_latest_readiness()
            validation = self.validator.validate("oura_readiness", data)

            if not validation.valid:
                return validation.warning

            score = data.get("readiness_score", 0)

            # Determine recommendation
            if score >= 85:
                recommendation = "✅ **Excellent!** Great day for high-intensity training. Your body is well-recovered."
                workout_type = "High intensity (HIIT, heavy lifting, sprints)"
            elif score >= 70:
                recommendation = "👍 **Good to go!** Moderate exercise recommended. Save the all-out efforts for a better day."
                workout_type = "Moderate (steady cardio, moderate weights, yoga)"
            elif score >= 50:
                recommendation = "⚠️ **Take it easy.** Consider lighter activity or active recovery."
                workout_type = "Light (walking, stretching, gentle yoga)"
            else:
                recommendation = "🛑 **Rest day recommended.** Your body needs recovery. Honor the signals."
                workout_type = "Rest or very light movement"

            result = f"""Exercise Readiness ({validation.latest_date}):

📊 **Readiness Score: {score}/100**

{recommendation}

💡 **Suggested Workout Type**: {workout_type}

📈 **Contributing Factors**
• Recovery Index: {data.get('recovery_index', 'N/A')}
• Resting HR: {data.get('resting_heart_rate', 'N/A')} bpm
• HRV Balance: {data.get('hrv_balance', 'N/A')}
• Temperature Deviation: {data.get('temperature_deviation', 'N/A')}°C

🔍 **Component Scores**
• Sleep Balance: {data.get('score_sleep_balance', 'N/A')}/100
• Previous Night: {data.get('score_previous_night', 'N/A')}/100
• Activity Balance: {data.get('score_activity_balance', 'N/A')}/100
• HRV Balance: {data.get('score_hrv_balance', 'N/A')}/100"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_activity_trends(days: int = 7) -> str:
            """Get activity trends over a period of time.

            Args:
                days: Number of days to analyze (default 7)

            Use this for questions about activity patterns, weekly activity, or step trends.
            """
            df = await self.queries.get_activity_trends(days)

            if df.empty:
                return f"No activity data found for the last {days} days."

            validation = self.validator.validate(
                "oura_activity",
                df.to_dict("records") if not df.empty else None,
            )

            # Calculate statistics
            avg_steps = df["steps"].mean()
            avg_calories = df["calories_total"].mean()
            avg_active = df["total_active_minutes"].mean()
            days_above_10k = len(df[df["steps"] >= 10000])

            # Build trend line
            trend_lines = []
            for _, row in df.tail(7).iterrows():
                d = row.get("date", "N/A")
                steps = row.get("steps", 0)
                emoji = "🌟" if steps >= 10000 else "📈" if steps >= 7500 else "📊"
                trend_lines.append(f"{emoji} {d}: {steps:,} steps")

            trend_data = "\n".join(trend_lines)

            result = f"""Activity Trends (Last {days} Days):

📊 **Averages**
• Daily Steps: {avg_steps:,.0f}
• Daily Calories: {avg_calories:,.0f} kcal
• Active Minutes: {avg_active:.0f} min/day
• Days ≥ 10k Steps: {days_above_10k}/{len(df)}

📅 **Recent Days**
{trend_data}

💡 **Assessment**
• Step Goal: {'Crushing it! 🎉' if avg_steps >= 10000 else 'On track 👍' if avg_steps >= 7500 else 'Room for improvement 💪'}
• Activity Level: {'Very Active' if avg_active >= 60 else 'Active' if avg_active >= 30 else 'Lightly Active'}"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_recent_workouts(days: int = 7) -> str:
            """Get recent workout history.

            Args:
                days: Number of days to look back (default 7)

            Use this when the user asks about their workouts, exercise history, or training log.
            """
            df = await self.queries.get_recent_workouts(days)

            if df.empty:
                return f"No workouts recorded in the last {days} days. Make sure to log workouts in the Oura app!"

            # Format workouts
            workout_lines = []
            for _, row in df.iterrows():
                d = row.get("date", "N/A")
                activity = row.get("activity", "Unknown")
                duration = row.get("duration_minutes", 0)
                calories = row.get("calories", 0)
                intensity = row.get("intensity", "N/A")
                workout_lines.append(
                    f"• {d}: {activity} - {duration:.0f} min, {calories:.0f} kcal ({intensity})"
                )

            workouts_text = "\n".join(workout_lines[:10])  # Limit to 10

            # Summary stats
            total_workouts = len(df)
            total_duration = df["duration_minutes"].sum()
            total_calories = df["calories"].sum()

            return f"""Recent Workouts (Last {days} Days):

📊 **Summary**
• Total Workouts: {total_workouts}
• Total Duration: {total_duration:.0f} minutes ({total_duration/60:.1f} hours)
• Total Calories: {total_calories:,.0f} kcal

🏋️ **Workout Log**
{workouts_text}

💡 **Tip**: Aim for 150 min of moderate activity or 75 min of vigorous activity per week."""

        @tool
        async def get_recovery_trends(days: int = 7) -> str:
            """Analyze recovery and readiness trends over time.

            Args:
                days: Number of days to analyze (default 7)

            Use this when the user asks about recovery patterns, readiness trends, or training load.
            """
            df = await self.queries.get_readiness_trends(days)

            if df.empty:
                return f"No readiness data found for the last {days} days."

            validation = self.validator.validate(
                "oura_readiness",
                df.to_dict("records") if not df.empty else None,
            )

            # Calculate statistics
            avg_score = df["readiness_score"].mean()
            min_score = df["readiness_score"].min()
            max_score = df["readiness_score"].max()
            avg_rhr = df["resting_heart_rate"].mean()
            avg_hrv_balance = df["hrv_balance"].mean() if "hrv_balance" in df else None

            # Determine trend
            recent_avg = df["readiness_score"].tail(3).mean()
            earlier_avg = df["readiness_score"].head(3).mean()
            if recent_avg > earlier_avg + 5:
                trend = "📈 Improving"
            elif recent_avg < earlier_avg - 5:
                trend = "📉 Declining - consider more rest"
            else:
                trend = "➡️ Stable"

            # Build trend line
            trend_lines = []
            for _, row in df.tail(7).iterrows():
                d = row.get("date", "N/A")
                score = row.get("readiness_score", 0)
                emoji = "🟢" if score >= 85 else "🟡" if score >= 70 else "🔴"
                trend_lines.append(f"{emoji} {d}: {score}")

            trend_data = "\n".join(trend_lines)

            result = f"""Recovery Trends (Last {days} Days):

📊 **Readiness**
• Average Score: {avg_score:.0f}/100
• Range: {min_score:.0f} - {max_score:.0f}
• Trend: {trend}

❤️ **Heart Rate**
• Avg Resting HR: {avg_rhr:.0f} bpm
• HRV Balance: {avg_hrv_balance:.1f if avg_hrv_balance else 'N/A'}

📅 **Recent Days**
{trend_data}

💡 **Recovery Tips**
• Consistent sleep schedule improves recovery
• Balance training with rest days
• Watch for elevated RHR (sign of stress or overtraining)"""

            if validation.stale:
                result = f"{validation.warning}\n\n{result}"

            return result

        @tool
        async def get_workout_by_type(activity_type: str) -> str:
            """Get workouts filtered by activity type.

            Args:
                activity_type: Type of workout (e.g., "running", "cycling", "strength")

            Use this when the user asks about specific workout types.
            """
            df = await self.queries.get_workouts_by_type(activity_type, days=90)

            if df.empty:
                return f"No '{activity_type}' workouts found in the last 90 days."

            # Summary
            total = len(df)
            total_duration = df["duration_minutes"].sum()
            total_calories = df["calories"].sum()
            total_distance = df["distance_km"].sum() if "distance_km" in df else 0
            avg_duration = df["duration_minutes"].mean()

            # Recent workouts
            recent_lines = []
            for _, row in df.head(5).iterrows():
                d = row.get("date", "N/A")
                duration = row.get("duration_minutes", 0)
                calories = row.get("calories", 0)
                recent_lines.append(f"• {d}: {duration:.0f} min, {calories:.0f} kcal")

            recent_text = "\n".join(recent_lines)

            return f"""{activity_type.title()} Workouts (Last 90 Days):

📊 **Summary**
• Total Sessions: {total}
• Total Duration: {total_duration:.0f} min ({total_duration/60:.1f} hours)
• Total Calories: {total_calories:,.0f} kcal
• Total Distance: {total_distance:.1f} km
• Avg Duration: {avg_duration:.0f} min/session

🏃 **Recent Sessions**
{recent_text}

💡 Keep up the consistency! Regular {activity_type} is great for your health."""

        return [
            get_today_activity,
            check_exercise_readiness,
            get_activity_trends,
            get_recent_workouts,
            get_recovery_trends,
            get_workout_by_type,
        ]
