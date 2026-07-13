"""
Supabase Memory System for Deep Agent

Integrates persistent, multi-user memory for oura-agent:
- Episodic Memory: Conversation history with embeddings
- Semantic Memory: Goals, baselines, user preferences
- Procedural Memory: What the agent has learned about this user

Tables:
- user_profiles: User baselines, preferences, health goals
- conversations: Query/response pairs with timestamps
- embeddings: Vector embeddings for semantic search
- alerts_history: What alerts have been sent (dedupe)
- agent_state: Per-user tracking of agent decisions

Usage:
    memory = SupabaseMemory(supabase_url, supabase_key)

    # Store conversation
    await memory.save_conversation(
        user_id="123456",
        query="How did I sleep?",
        response="You had 7.2 hours...",
        specialists=["sleep_analyst"]
    )

    # Recall past advice
    similar = await memory.search_conversations(
        user_id="123456",
        query="Remember when you told me about sleep",
        top_k=3
    )

    # Get user goals & baselines
    profile = await memory.get_user_profile(user_id="123456")
    # → {"goals": [...], "baselines": {...}, "preferences": {...}}
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseMemory:
    """
    Persistent memory system for oura-agent using Supabase.

    Handles episodic (conversations), semantic (goals/baselines),
    and procedural (learned behaviors) memory.
    """

    def __init__(self, url: str, key: str):
        """Initialize Supabase client.

        Args:
            url: Supabase project URL
            key: Supabase anon/service key
        """
        self.supabase: Client = create_client(url, key)
        self.url = url
        self.key = key

    # ========================================================================
    # EPISODIC MEMORY (Conversations)
    # ========================================================================

    async def save_conversation(
        self,
        user_id: str,
        query: str,
        response: str,
        specialists: list[str],
        channel_id: str,
    ) -> dict[str, Any]:
        """Save a conversation turn to episodic memory.

        Args:
            user_id: Discord user ID
            query: User's question
            response: Agent's response
            specialists: Which specialists were called
            channel_id: Discord channel ID

        Returns:
            Conversation record with ID
        """
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "channel_id": channel_id,
            "query": query,
            "response": response,
            "specialists": specialists,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = self.supabase.table("conversations").insert(record).execute()
            logger.info(f"Saved conversation {record['id']} for user {user_id}")
            return record
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        """Search past conversations using semantic similarity.

        Finds similar past queries to provide context.

        Args:
            user_id: Discord user ID
            query: Search query
            top_k: Number of results
            days: How far back to search

        Returns:
            List of similar conversations
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            # Query conversations for this user
            result = (
                self.supabase.table("conversations")
                .select("id, query, response, specialists, created_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff_date)
                .order("created_at", desc=True)
                .limit(100)  # Fetch recent ones for similarity search
                .execute()
            )

            conversations = result.data or []
            logger.info(f"Found {len(conversations)} conversations for user {user_id}")

            # TODO: Implement vector similarity search
            # For now, return most recent conversations
            # In production, use pgvector + embeddings for semantic search
            return conversations[:top_k]

        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get conversation history for context window.

        Args:
            user_id: Discord user ID
            limit: Number of recent conversations

        Returns:
            List of recent conversations
        """
        try:
            result = (
                self.supabase.table("conversations")
                .select("query, response, specialists, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    # ========================================================================
    # SEMANTIC MEMORY (Goals, Baselines, Preferences)
    # ========================================================================

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user's health profile (goals, baselines, preferences).

        Args:
            user_id: Discord user ID

        Returns:
            User profile with goals, baselines, preferences
        """
        try:
            result = (
                self.supabase.table("user_profiles")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if result.data:
                logger.info(f"Retrieved profile for user {user_id}")
                return result.data
            else:
                logger.info(f"No profile found for user {user_id}, returning defaults")
                return self._default_profile(user_id)

        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return self._default_profile(user_id)

    async def update_user_goals(
        self,
        user_id: str,
        goals: dict[str, Any],
    ) -> dict[str, Any]:
        """Update user's health goals.

        Args:
            user_id: Discord user ID
            goals: Goals object (e.g., {"sleep_hours": 8, "steps": 10000})

        Returns:
            Updated profile
        """
        try:
            data = {
                "user_id": user_id,
                "goals": goals,
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = (
                self.supabase.table("user_profiles")
                .upsert(data, on_conflict="user_id")
                .execute()
            )

            logger.info(f"Updated goals for user {user_id}: {goals}")
            return result.data[0] if result.data else data

        except Exception as e:
            logger.error(f"Failed to update goals: {e}")
            raise

    async def update_user_baselines(
        self,
        user_id: str,
        baselines: dict[str, Any],
    ) -> dict[str, Any]:
        """Update user's personal health baselines.

        Args:
            user_id: Discord user ID
            baselines: Baselines (e.g., {"hrv_ms": 42, "resting_hr": 58})

        Returns:
            Updated profile
        """
        try:
            data = {
                "user_id": user_id,
                "baselines": baselines,
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = (
                self.supabase.table("user_profiles")
                .upsert(data, on_conflict="user_id")
                .execute()
            )

            logger.info(f"Updated baselines for user {user_id}: {baselines}")
            return result.data[0] if result.data else data

        except Exception as e:
            logger.error(f"Failed to update baselines: {e}")
            raise

    # ========================================================================
    # PROCEDURAL MEMORY (Alert History, Agent Decisions)
    # ========================================================================

    async def log_alert_sent(
        self,
        user_id: str,
        alert_type: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Log that an alert was sent (for deduplication).

        Args:
            user_id: Discord user ID
            alert_type: Type of alert (e.g., "sync", "fatigue", "recovery")
            context: Context data (e.g., {"hrv_drop_percent": 20})

        Returns:
            Alert record
        """
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "alert_type": alert_type,
            "context": context,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = self.supabase.table("alerts_history").insert(record).execute()
            logger.info(f"Logged {alert_type} alert for user {user_id}")
            return record
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
            raise

    async def get_recent_alerts(
        self,
        user_id: str,
        alert_type: str,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get recent alerts of a type (to avoid repeating).

        Args:
            user_id: Discord user ID
            alert_type: Type of alert to query
            hours: Look back this many hours

        Returns:
            List of recent alerts
        """
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        try:
            result = (
                self.supabase.table("alerts_history")
                .select("created_at, context")
                .eq("user_id", user_id)
                .eq("alert_type", alert_type)
                .gte("created_at", cutoff_time)
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []

    async def should_alert(
        self,
        user_id: str,
        alert_type: str,
        min_hours_between: int = 24,
    ) -> bool:
        """Check if enough time has passed since last alert of this type.

        Args:
            user_id: Discord user ID
            alert_type: Type of alert
            min_hours_between: Minimum hours between alerts

        Returns:
            True if we should send the alert
        """
        recent = await self.get_recent_alerts(
            user_id, alert_type, hours=min_hours_between
        )
        return len(recent) == 0

    # ========================================================================
    # AGENT STATE (what the agent has decided/learned)
    # ========================================================================

    async def update_agent_state(
        self,
        user_id: str,
        state_key: str,
        state_value: Any,
    ) -> None:
        """Update agent state tracking for a user.

        Args:
            user_id: Discord user ID
            state_key: State key (e.g., "last_sleep_alert", "preferred_specialists")
            state_value: State value
        """
        try:
            current = await self.get_user_profile(user_id)
            state = current.get("agent_state", {})
            state[state_key] = state_value

            data = {
                "user_id": user_id,
                "agent_state": state,
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("user_profiles").upsert(data, on_conflict="user_id").execute()

            logger.info(f"Updated agent state for user {user_id}: {state_key}")

        except Exception as e:
            logger.error(f"Failed to update agent state: {e}")
            raise

    async def get_agent_state(self, user_id: str) -> dict[str, Any]:
        """Get agent state for a user.

        Args:
            user_id: Discord user ID

        Returns:
            Agent state dict
        """
        try:
            profile = await self.get_user_profile(user_id)
            return profile.get("agent_state", {})
        except Exception as e:
            logger.error(f"Failed to get agent state: {e}")
            return {}

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _default_profile(self, user_id: str) -> dict[str, Any]:
        """Return default profile for new user.

        Args:
            user_id: Discord user ID

        Returns:
            Default profile
        """
        return {
            "user_id": user_id,
            "goals": {},
            "baselines": {},
            "preferences": {},
            "agent_state": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }


async def init_supabase_memory(url: str, key: str) -> SupabaseMemory:
    """Initialize Supabase memory system.

    Call this once at startup.

    Args:
        url: Supabase project URL
        key: Supabase anon/service key

    Returns:
        SupabaseMemory instance
    """
    memory = SupabaseMemory(url, key)
    logger.info("Supabase memory system initialized")
    return memory
