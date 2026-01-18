"""Main entry point for Oura Health Agent.

Orchestrates the Discord polling loop, message processing,
and agent interactions.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from uuid import uuid4

from database.connection import close_engine, get_async_session, test_connection
from discord.client import DiscordClient
from memory.embeddings import EmbeddingService, get_embedding_service
from memory.episodic import EpisodicMemory
from memory.long_term import LongTermMemory
from memory.working import WorkingMemory, get_working_memory
from src.agents.supervisor import SupervisorAgent
from src.config import get_config, setup_logging
from src.healthcheck import run_health_server_async, update_health_state

logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def process_message(
    agent: SupervisorAgent,
    discord_client: DiscordClient,
    message,
    config,
    episodic_memory: EpisodicMemory,
    long_term_memory: LongTermMemory,
) -> None:
    """Process a single Discord message through the multi-agent system.

    Args:
        agent: Supervisor agent instance (orchestrates specialist agents)
        discord_client: Discord client instance
        message: Discord message to process
        config: Application configuration
        episodic_memory: Episodic memory instance
        long_term_memory: Long-term memory instance
    """
    session_id = str(uuid4())

    try:
        logger.info(
            f"Processing message {message.id} from {message.author_username}: "
            f"{message.content[:50]}..."
        )

        # Process the message through the multi-agent system
        response = await agent.process_message(
            message=message.content,
            user_id=message.author_id,
            channel_id=message.channel_id,
            session_id=session_id,
        )

        # Send response to Discord
        await discord_client.send_health_response(
            channel_id=message.channel_id,
            user_id=message.author_id,
            response_text=response,
        )

        # Mark message as processed
        await discord_client.mark_as_processed(
            channel_id=message.channel_id,
            message_id=message.id,
        )

        # Save to episodic memory for future recall
        async with get_async_session(config.database.connection_string) as session:
            await episodic_memory.save_health_insight(
                session=session,
                user_id=message.author_id,
                session_id=session_id,
                user_query=message.content,
                agent_response=response,
            )

        logger.info(f"Successfully processed message {message.id}")

    except Exception as e:
        logger.error(f"Error processing message {message.id}: {e}", exc_info=True)

        # Send error response to user
        try:
            await discord_client.send_error_response(
                channel_id=message.channel_id,
                user_id=message.author_id,
                error_message=str(e),
            )
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")


async def polling_loop(
    discord_client: DiscordClient,
    agent: SupervisorAgent,
    config,
    episodic_memory: EpisodicMemory,
    long_term_memory: LongTermMemory,
) -> None:
    """Main polling loop that checks for new messages.

    Args:
        discord_client: Discord client instance
        agent: Supervisor agent (orchestrates specialist agents)
        config: Application configuration
        episodic_memory: Episodic memory instance
        long_term_memory: Long-term memory instance
    """
    poll_interval = config.discord.poll_interval
    channel_id = config.discord.health_channel_id
    window_minutes = config.discord.message_window_minutes

    logger.info(
        f"Starting polling loop: channel={channel_id}, "
        f"interval={poll_interval}s, window={window_minutes}min"
    )

    while not shutdown_event.is_set():
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
                if shutdown_event.is_set():
                    break

                await process_message(
                    agent=agent,
                    discord_client=discord_client,
                    message=message,
                    config=config,
                    episodic_memory=episodic_memory,
                    long_term_memory=long_term_memory,
                )

            # If run_once mode, exit after first poll
            if config.run_once:
                logger.info("Run once mode - exiting after first poll")
                break

        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)

        # Wait for next poll (with shutdown check)
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=poll_interval,
            )
        except asyncio.TimeoutError:
            # Normal timeout - continue polling
            pass

    logger.info("Polling loop stopped")


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Load configuration
    try:
        config = get_config()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Set up logging
    setup_logging(config.log_level)
    logger.info("Oura Health Agent starting...")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Test database connection
    logger.info("Testing database connection...")
    if not await test_connection(config.database.connection_string):
        logger.error("Database connection failed")
        return 1

    # Initialize Discord client
    discord_client = DiscordClient(
        token=config.discord.bot_token,
        processed_emoji=config.discord.processed_emoji,
    )

    # Test Discord connection
    logger.info("Testing Discord connection...")
    if not await discord_client.test_connection():
        logger.error("Discord connection failed")
        return 1

    # Initialize embedding service
    embedding_service = get_embedding_service(
        base_url=config.ollama.base_url,
        model=config.ollama.model,
        embedding_dim=config.ollama.embedding_dim,
    )

    # Test embedding service
    logger.info("Testing embedding service...")
    if not await embedding_service.test_connection():
        logger.warning("Embedding service unavailable - episodic memory disabled")

    # Initialize memory systems
    # Note: psycopg_connection_string strips +asyncpg for psycopg compatibility
    working_memory = get_working_memory(config.database.psycopg_connection_string)
    await working_memory.setup()

    episodic_memory = EpisodicMemory(embedding_service=embedding_service)
    long_term_memory = LongTermMemory()

    # Get checkpointer for agent
    checkpointer = await working_memory.get_checkpointer()

    # Initialize multi-agent supervisor
    logger.info("Initializing multi-agent health system...")
    agent = SupervisorAgent(
        connection_string=config.database.connection_string,
        embedding_service=embedding_service,
        api_key=config.llm.api_key,
        model=config.llm.model,
        checkpointer=checkpointer,
    )

    logger.info("Oura Health Agent (multi-agent system) initialized successfully")
    logger.info(
        f"  Specialist agents: sleep_analyst, fitness_coach, memory_keeper, data_auditor"
    )

    try:
        # Update health state now that we're initialized
        update_health_state(database_ok=True, discord_ok=True)

        # Start health server in background
        logger.info("Starting health check server on port 8080...")
        health_task = asyncio.create_task(run_health_server_async(port=8080))

        # Start polling loop
        await polling_loop(
            discord_client=discord_client,
            agent=agent,
            config=config,
            episodic_memory=episodic_memory,
            long_term_memory=long_term_memory,
        )

    finally:
        # Cancel health server
        if 'health_task' in locals():
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
        # Cleanup
        logger.info("Cleaning up...")
        await embedding_service.close()
        await working_memory.close()
        await close_engine()
        logger.info("Oura Health Agent stopped")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
