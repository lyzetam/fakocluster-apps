"""Working Memory - LangGraph conversation state persistence.

Uses LangGraph's PostgresSaver checkpointer to maintain conversation
state across turns. Thread ID is based on Discord user + channel for
multi-turn conversations.
"""

import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


def create_thread_id(user_id: str, channel_id: str) -> str:
    """Create a unique thread ID for a user in a channel.

    This allows multi-turn conversations within the same channel,
    with each user having their own conversation thread.

    Args:
        user_id: Discord user ID
        channel_id: Discord channel ID

    Returns:
        Unique thread identifier
    """
    return f"oura-health-{user_id}-{channel_id}"


class WorkingMemory:
    """Working memory using LangGraph PostgresSaver.

    Maintains conversation state across multiple turns, allowing
    the agent to remember context within a conversation session.
    """

    def __init__(self, connection_string: str):
        """Initialize working memory.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self._checkpointer: Optional[AsyncPostgresSaver] = None
        self._pool: Optional[AsyncConnectionPool] = None

    async def get_checkpointer(self) -> AsyncPostgresSaver:
        """Get or create the async checkpointer.

        Returns:
            AsyncPostgresSaver instance
        """
        if self._checkpointer is None:
            raise RuntimeError("WorkingMemory not initialized. Call setup() first.")
        return self._checkpointer

    async def setup(self) -> None:
        """Set up the checkpointer tables.

        Creates necessary tables for storing checkpoints.
        Should be called once at startup.
        """
        if self._checkpointer is not None:
            logger.info("Working memory already initialized")
            return

        # A pool, not one connection held for the life of the pod: Postgres
        # drops idle connections, and a lone connection never came back
        # ("the connection is closed" on every briefing until a restart).
        # check_connection pings each connection before handing it out and
        # replaces a dead one.
        self._pool = AsyncConnectionPool(
            self.connection_string,
            min_size=1,
            max_size=4,
            open=False,
            check=AsyncConnectionPool.check_connection,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        await self._pool.open(wait=True)
        self._checkpointer = AsyncPostgresSaver(self._pool)
        await self._checkpointer.setup()
        logger.info("Working memory checkpointer initialized")
        logger.info("Working memory tables created/verified")

    def get_config(self, user_id: str, channel_id: str) -> dict:
        """Get LangGraph config for a conversation thread.

        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID

        Returns:
            Config dict with thread_id for LangGraph
        """
        thread_id = create_thread_id(user_id, channel_id)
        return {"configurable": {"thread_id": thread_id}}

    async def clear_thread(self, user_id: str, channel_id: str) -> bool:
        """Clear the conversation state for a thread.

        Useful for "reset conversation" commands.

        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID

        Returns:
            True if successful
        """
        try:
            thread_id = create_thread_id(user_id, channel_id)
            if self._pool is None:
                raise RuntimeError("WorkingMemory not initialized. Call setup() first.")

            # Delete all checkpoints for this thread
            # Note: This depends on LangGraph's internal table structure
            # A cleaner approach would be to use LangGraph's API if available
            async with self._pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (thread_id,),
                )
                await cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (thread_id,),
                )

            logger.info(f"Cleared working memory for thread: {thread_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing working memory: {e}")
            return False

    async def close(self) -> None:
        """Close the checkpointer's connection pool."""
        if self._pool is not None:
            try:
                await self._pool.close()
                logger.info("Working memory pool closed")
            except Exception as e:
                logger.warning(f"Error closing working memory pool: {e}")
            finally:
                self._pool = None
                self._checkpointer = None
                logger.info("Working memory closed")


# Factory function for dependency injection
_working_memory: Optional[WorkingMemory] = None


def get_working_memory(connection_string: str) -> WorkingMemory:
    """Get singleton working memory instance.

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        WorkingMemory instance
    """
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory(connection_string)
    return _working_memory
