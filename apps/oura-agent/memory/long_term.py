"""Long-Term Memory - User goals, baselines, and preferences.

Stores persistent user data that persists across all conversations:
- Health goals (e.g., "sleep 8 hours", "10k steps")
- Computed baselines (e.g., average HRV, typical sleep efficiency)
- User preferences (e.g., preferred workout times)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class HealthGoal:
    """A user's health goal."""

    id: str
    user_id: str
    goal_type: str  # sleep_duration, step_count, hrv_target, etc.
    target_value: Optional[float]
    target_text: Optional[str]
    status: str  # active, achieved, abandoned
    created_at: datetime
    achieved_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthGoal":
        """Create from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            user_id=data.get("user_id", ""),
            goal_type=data.get("goal_type", ""),
            target_value=data.get("target_value"),
            target_text=data.get("target_text"),
            status=data.get("status", "active"),
            created_at=data.get("created_at", datetime.now()),
            achieved_at=data.get("achieved_at"),
        )


@dataclass
class HealthBaseline:
    """A computed health baseline for a user."""

    id: str
    user_id: str
    metric: str  # hrv_avg, resting_hr, sleep_efficiency, etc.
    baseline_value: float
    sample_size: int
    computed_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthBaseline":
        """Create from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            user_id=data.get("user_id", ""),
            metric=data.get("metric", ""),
            baseline_value=data.get("baseline_value", 0.0),
            sample_size=data.get("sample_size", 0),
            computed_at=data.get("computed_at", datetime.now()),
        )


class LongTermMemory:
    """Long-term memory for user goals and baselines.

    Provides persistence for information that should survive across
    all conversations:
    - Health goals the user has set
    - Computed baselines for personalized comparisons
    - User preferences for response personalization
    """

    GOALS_TABLE = "health_user_goals"
    BASELINES_TABLE = "health_baselines"

    # Standard goal types for health metrics
    GOAL_TYPES = {
        "sleep_duration": "hours of sleep per night",
        "sleep_score": "minimum sleep score",
        "step_count": "daily steps",
        "active_calories": "active calories burned daily",
        "hrv_target": "target HRV",
        "readiness_score": "minimum readiness score",
        "workout_frequency": "workouts per week",
        "meditation_minutes": "meditation minutes per day",
    }

    # Standard baseline metrics
    BASELINE_METRICS = {
        "hrv_avg": "average HRV",
        "resting_hr": "resting heart rate",
        "sleep_efficiency": "sleep efficiency percentage",
        "sleep_duration_avg": "average sleep duration",
        "step_count_avg": "average daily steps",
        "readiness_avg": "average readiness score",
        "activity_score_avg": "average activity score",
    }

    async def set_goal(
        self,
        session: AsyncSession,
        user_id: str,
        goal_type: str,
        target_value: Optional[float] = None,
        target_text: Optional[str] = None,
    ) -> Optional[str]:
        """Set a health goal for a user.

        If a goal of the same type already exists, it will be replaced.

        Args:
            session: Database session
            user_id: Discord user ID
            goal_type: Type of goal (see GOAL_TYPES)
            target_value: Numeric target (optional)
            target_text: Text description of goal (optional)

        Returns:
            ID of the created goal
        """
        try:
            # Deactivate existing goal of same type
            await session.execute(
                text(f"""
                    UPDATE {self.GOALS_TABLE}
                    SET status = 'replaced'
                    WHERE user_id = :user_id AND goal_type = :goal_type AND status = 'active'
                """),
                {"user_id": user_id, "goal_type": goal_type},
            )

            # Create new goal
            goal_id = str(uuid4())
            await session.execute(
                text(f"""
                    INSERT INTO {self.GOALS_TABLE}
                    (id, user_id, goal_type, target_value, target_text, status)
                    VALUES (:id, :user_id, :goal_type, :target_value, :target_text, 'active')
                """),
                {
                    "id": goal_id,
                    "user_id": user_id,
                    "goal_type": goal_type,
                    "target_value": target_value,
                    "target_text": target_text,
                },
            )

            logger.info(f"Set goal {goal_type} for user {user_id}")
            return goal_id

        except Exception as e:
            logger.error(f"Error setting goal: {e}")
            return None

    async def get_active_goals(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> list[HealthGoal]:
        """Get all active goals for a user.

        Args:
            session: Database session
            user_id: Discord user ID

        Returns:
            List of active health goals
        """
        try:
            result = await session.execute(
                text(f"""
                    SELECT id, user_id, goal_type, target_value, target_text,
                           status, created_at, achieved_at
                    FROM {self.GOALS_TABLE}
                    WHERE user_id = :user_id AND status = 'active'
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id},
            )

            rows = result.fetchall()
            return [
                HealthGoal(
                    id=str(row.id),
                    user_id=row.user_id,
                    goal_type=row.goal_type,
                    target_value=row.target_value,
                    target_text=row.target_text,
                    status=row.status,
                    created_at=row.created_at,
                    achieved_at=row.achieved_at,
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting active goals: {e}")
            return []

    async def mark_goal_achieved(
        self,
        session: AsyncSession,
        goal_id: str,
    ) -> bool:
        """Mark a goal as achieved.

        Args:
            session: Database session
            goal_id: Goal ID to mark as achieved

        Returns:
            True if successful
        """
        try:
            await session.execute(
                text(f"""
                    UPDATE {self.GOALS_TABLE}
                    SET status = 'achieved', achieved_at = NOW()
                    WHERE id = :id
                """),
                {"id": goal_id},
            )
            logger.info(f"Marked goal {goal_id} as achieved")
            return True

        except Exception as e:
            logger.error(f"Error marking goal achieved: {e}")
            return False

    async def abandon_goal(
        self,
        session: AsyncSession,
        goal_id: str,
    ) -> bool:
        """Mark a goal as abandoned.

        Args:
            session: Database session
            goal_id: Goal ID to abandon

        Returns:
            True if successful
        """
        try:
            await session.execute(
                text(f"""
                    UPDATE {self.GOALS_TABLE}
                    SET status = 'abandoned'
                    WHERE id = :id
                """),
                {"id": goal_id},
            )
            logger.info(f"Abandoned goal {goal_id}")
            return True

        except Exception as e:
            logger.error(f"Error abandoning goal: {e}")
            return False

    async def set_baseline(
        self,
        session: AsyncSession,
        user_id: str,
        metric: str,
        baseline_value: float,
        sample_size: int,
    ) -> Optional[str]:
        """Set or update a health baseline for a user.

        Args:
            session: Database session
            user_id: Discord user ID
            metric: Metric name (see BASELINE_METRICS)
            baseline_value: Computed baseline value
            sample_size: Number of data points used in computation

        Returns:
            ID of the baseline record
        """
        try:
            baseline_id = str(uuid4())

            # Upsert - replace existing baseline for this metric
            await session.execute(
                text(f"""
                    INSERT INTO {self.BASELINES_TABLE}
                    (id, user_id, metric, baseline_value, sample_size, computed_at)
                    VALUES (:id, :user_id, :metric, :baseline_value, :sample_size, NOW())
                    ON CONFLICT (user_id, metric)
                    DO UPDATE SET
                        baseline_value = :baseline_value,
                        sample_size = :sample_size,
                        computed_at = NOW()
                """),
                {
                    "id": baseline_id,
                    "user_id": user_id,
                    "metric": metric,
                    "baseline_value": baseline_value,
                    "sample_size": sample_size,
                },
            )

            logger.info(f"Set baseline {metric}={baseline_value} for user {user_id}")
            return baseline_id

        except Exception as e:
            logger.error(f"Error setting baseline: {e}")
            return None

    async def get_baselines(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> dict[str, HealthBaseline]:
        """Get all baselines for a user.

        Args:
            session: Database session
            user_id: Discord user ID

        Returns:
            Dict mapping metric name to HealthBaseline
        """
        try:
            result = await session.execute(
                text(f"""
                    SELECT id, user_id, metric, baseline_value, sample_size, computed_at
                    FROM {self.BASELINES_TABLE}
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id},
            )

            rows = result.fetchall()
            return {
                row.metric: HealthBaseline(
                    id=str(row.id),
                    user_id=row.user_id,
                    metric=row.metric,
                    baseline_value=row.baseline_value,
                    sample_size=row.sample_size,
                    computed_at=row.computed_at,
                )
                for row in rows
            }

        except Exception as e:
            logger.error(f"Error getting baselines: {e}")
            return {}

    async def get_baseline(
        self,
        session: AsyncSession,
        user_id: str,
        metric: str,
    ) -> Optional[HealthBaseline]:
        """Get a specific baseline for a user.

        Args:
            session: Database session
            user_id: Discord user ID
            metric: Metric name

        Returns:
            HealthBaseline if found, None otherwise
        """
        baselines = await self.get_baselines(session, user_id)
        return baselines.get(metric)

    async def format_goals_for_context(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> str:
        """Format user goals for agent context.

        Creates a human-readable summary of user's health goals
        to include in the agent's context.

        Args:
            session: Database session
            user_id: Discord user ID

        Returns:
            Formatted string describing user's goals
        """
        goals = await self.get_active_goals(session, user_id)

        if not goals:
            return "No active health goals set."

        lines = ["User's Active Health Goals:"]
        for goal in goals:
            desc = self.GOAL_TYPES.get(goal.goal_type, goal.goal_type)
            if goal.target_value:
                lines.append(f"- {desc}: {goal.target_value}")
            elif goal.target_text:
                lines.append(f"- {desc}: {goal.target_text}")
            else:
                lines.append(f"- {desc}")

        return "\n".join(lines)

    async def format_baselines_for_context(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> str:
        """Format user baselines for agent context.

        Creates a human-readable summary of user's health baselines
        to include in the agent's context.

        Args:
            session: Database session
            user_id: Discord user ID

        Returns:
            Formatted string describing user's baselines
        """
        baselines = await self.get_baselines(session, user_id)

        if not baselines:
            return "No health baselines computed yet."

        lines = ["User's Health Baselines:"]
        for metric, baseline in baselines.items():
            desc = self.BASELINE_METRICS.get(metric, metric)
            lines.append(f"- {desc}: {baseline.baseline_value:.1f} (n={baseline.sample_size})")

        return "\n".join(lines)
