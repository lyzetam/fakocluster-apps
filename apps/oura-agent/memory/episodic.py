"""Episodic Memory - Past health conversations with vector search.

Stores health conversation summaries with embeddings for semantic retrieval.
Allows queries like "What did you tell me about my HRV last week?"
Uses PostgreSQL with pgvector for vector similarity search.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from memory.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class EpisodicMemoryEntry:
    """A single episodic memory entry."""

    id: str
    user_id: str
    session_id: str
    summary: str
    query: Optional[str]
    outcome: Optional[str]
    health_metrics: Optional[dict[str, Any]]
    created_at: datetime
    similarity: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodicMemoryEntry":
        """Create entry from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            summary=data.get("summary", ""),
            query=data.get("query"),
            outcome=data.get("outcome"),
            health_metrics=data.get("health_metrics"),
            created_at=data.get("created_at", datetime.now()),
            similarity=data.get("similarity", 0.0),
        )


class EpisodicMemory:
    """Episodic memory store using PostgreSQL pgvector.

    Stores health conversation summaries and insights for semantic retrieval.
    """

    TABLE_NAME = "health_episodic_memory"

    def __init__(self, embedding_service: EmbeddingService):
        """Initialize episodic memory.

        Args:
            embedding_service: Service for generating embeddings
        """
        self.embedding_service = embedding_service

    async def store(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        summary: str,
        query: Optional[str] = None,
        outcome: Optional[str] = None,
        health_metrics: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a new episodic memory.

        Args:
            session: Database session
            user_id: Discord user ID
            session_id: Conversation session ID
            summary: Summary of the health conversation
            query: Original user query
            outcome: What insight or action was provided
            health_metrics: Key health metrics discussed (optional)

        Returns:
            ID of the created memory, or None if failed
        """
        try:
            # Generate embedding for the summary
            text_to_embed = f"{query or ''} {summary}"
            embedding = await self.embedding_service.embed(text_to_embed)

            # Prepare data
            memory_id = str(uuid4())

            query_sql = text(f"""
                INSERT INTO {self.TABLE_NAME}
                (id, user_id, session_id, summary, query, outcome, health_metrics, embedding)
                VALUES (:id, :user_id, :session_id, :summary, :query, :outcome, :health_metrics, :embedding)
            """)

            await session.execute(
                query_sql,
                {
                    "id": memory_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "summary": summary,
                    "query": query,
                    "outcome": outcome,
                    "health_metrics": json.dumps(health_metrics) if health_metrics else None,
                    "embedding": embedding,
                },
            )

            logger.info(f"Stored episodic memory: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            return None

    async def search(
        self,
        session: AsyncSession,
        search_text: str,
        user_id: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[EpisodicMemoryEntry]:
        """Search episodic memories by semantic similarity.

        Args:
            session: Database session
            search_text: Search query text
            user_id: Discord user ID
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of matching episodic memories
        """
        try:
            # Generate embedding for search text
            query_embedding = await self.embedding_service.embed(search_text)

            # Vector similarity search using cosine distance
            # pgvector uses 1 - cosine_distance for similarity
            query_sql = text(f"""
                SELECT
                    id, user_id, session_id, summary, query, outcome,
                    health_metrics, created_at,
                    1 - (embedding <=> :query_embedding::vector) as similarity
                FROM {self.TABLE_NAME}
                WHERE user_id = :user_id
                    AND 1 - (embedding <=> :query_embedding::vector) >= :threshold
                ORDER BY embedding <=> :query_embedding::vector
                LIMIT :limit
            """)

            result = await session.execute(
                query_sql,
                {
                    "query_embedding": query_embedding,
                    "user_id": user_id,
                    "threshold": threshold,
                    "limit": limit,
                },
            )

            rows = result.fetchall()

            entries = []
            for row in rows:
                health_metrics = None
                if row.health_metrics:
                    health_metrics = (
                        json.loads(row.health_metrics)
                        if isinstance(row.health_metrics, str)
                        else row.health_metrics
                    )

                entries.append(
                    EpisodicMemoryEntry(
                        id=str(row.id),
                        user_id=row.user_id,
                        session_id=row.session_id,
                        summary=row.summary,
                        query=row.query,
                        outcome=row.outcome,
                        health_metrics=health_metrics,
                        created_at=row.created_at,
                        similarity=row.similarity,
                    )
                )

            return entries

        except Exception as e:
            logger.error(f"Error searching episodic memory: {e}")
            return []

    async def get_recent(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 10,
    ) -> list[EpisodicMemoryEntry]:
        """Get recent episodic memories for a user.

        Args:
            session: Database session
            user_id: Discord user ID
            limit: Maximum number of results

        Returns:
            List of recent episodic memories
        """
        try:
            query_sql = text(f"""
                SELECT
                    id, user_id, session_id, summary, query, outcome,
                    health_metrics, created_at
                FROM {self.TABLE_NAME}
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = await session.execute(
                query_sql,
                {"user_id": user_id, "limit": limit},
            )

            rows = result.fetchall()

            entries = []
            for row in rows:
                health_metrics = None
                if row.health_metrics:
                    health_metrics = (
                        json.loads(row.health_metrics)
                        if isinstance(row.health_metrics, str)
                        else row.health_metrics
                    )

                entries.append(
                    EpisodicMemoryEntry(
                        id=str(row.id),
                        user_id=row.user_id,
                        session_id=row.session_id,
                        summary=row.summary,
                        query=row.query,
                        outcome=row.outcome,
                        health_metrics=health_metrics,
                        created_at=row.created_at,
                    )
                )

            return entries

        except Exception as e:
            logger.error(f"Error getting recent episodic memories: {e}")
            return []

    async def delete(self, session: AsyncSession, memory_id: str) -> bool:
        """Delete an episodic memory.

        Args:
            session: Database session
            memory_id: ID of memory to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query_sql = text(f"DELETE FROM {self.TABLE_NAME} WHERE id = :id")
            await session.execute(query_sql, {"id": memory_id})
            logger.info(f"Deleted episodic memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting episodic memory: {e}")
            return False

    async def save_health_insight(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        user_query: str,
        agent_response: str,
        key_metrics: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Save a health conversation as an episodic memory.

        Convenience method that creates a summary from query and response.

        Args:
            session: Database session
            user_id: Discord user ID
            session_id: Conversation session ID
            user_query: The user's original question
            agent_response: The agent's response
            key_metrics: Key health metrics discussed

        Returns:
            ID of the created memory
        """
        # Create a summary combining query and key insight
        summary = f"User asked about: {user_query[:200]}"
        if len(agent_response) > 500:
            outcome = agent_response[:500] + "..."
        else:
            outcome = agent_response

        return await self.store(
            session=session,
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            query=user_query,
            outcome=outcome,
            health_metrics=key_metrics,
        )
