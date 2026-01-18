"""Configuration for Oura Health Agent.

All configuration is loaded from environment variables or AWS Secrets Manager.
"""

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from externalconnections.fetch_secrets import (
    get_anthropic_secrets,
    get_database_secrets,
    get_discord_secrets,
    get_ollama_secrets,
    build_postgres_connection_string,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscordConfig:
    """Discord bot configuration."""

    bot_token: str
    guild_id: str
    health_channel_id: str
    poll_interval: int = 30  # seconds between polls
    message_window_minutes: int = 30  # only process messages from last N minutes
    processed_emoji: str = "\U0001FA7A"  # 🩺 stethoscope emoji

    def validate(self) -> bool:
        """Validate required Discord configuration."""
        if not self.bot_token:
            logger.error("DISCORD_BOT_TOKEN is required")
            return False
        if not self.health_channel_id:
            logger.error("DISCORD_HEALTH_CHANNEL_ID is required")
            return False
        return True


@dataclass
class LLMConfig:
    """LLM configuration for Claude Sonnet."""

    api_key: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3  # Lower for accuracy in health responses
    max_tokens: int = 4096

    def validate(self) -> bool:
        """Validate required LLM configuration."""
        if not self.api_key:
            logger.error("ANTHROPIC_API_KEY is required")
            return False
        return True


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration."""

    connection_string: str
    pool_size: int = 5
    max_overflow: int = 10

    @property
    def psycopg_connection_string(self) -> str:
        """Get connection string for psycopg (without asyncpg driver).

        LangGraph's AsyncPostgresSaver uses psycopg directly, which expects
        a standard PostgreSQL connection string without the +asyncpg driver.
        """
        conn_str = self.connection_string
        if "postgresql+asyncpg://" in conn_str:
            conn_str = conn_str.replace("postgresql+asyncpg://", "postgresql://")
        return conn_str

    def validate(self) -> bool:
        """Validate required database configuration."""
        if not self.connection_string:
            logger.error("DATABASE_URL or postgres credentials are required")
            return False
        return True


@dataclass
class OllamaConfig:
    """Ollama embedding service configuration."""

    base_url: str = "http://localhost:11434"
    model: str = "nomic-embed-text"
    embedding_dim: int = 768


@dataclass
class Config:
    """Main configuration container."""

    discord: DiscordConfig
    llm: LLMConfig
    database: DatabaseConfig
    ollama: OllamaConfig
    log_level: str = "INFO"
    run_once: bool = False  # If True, process once and exit

    def validate(self) -> bool:
        """Validate all configuration."""
        return all(
            [
                self.discord.validate(),
                self.llm.validate(),
                self.database.validate(),
            ]
        )


@lru_cache
def get_config() -> Config:
    """Load configuration from environment and AWS Secrets Manager.

    Returns:
        Config: Fully populated configuration object

    Raises:
        ValueError: If required configuration is missing
    """
    # Load secrets from AWS (with env var fallback)
    discord_secrets = get_discord_secrets()
    anthropic_secrets = get_anthropic_secrets()
    database_secrets = get_database_secrets()
    ollama_secrets = get_ollama_secrets()

    # Build database connection string
    db_connection_string = build_postgres_connection_string(database_secrets)

    # Discord config
    discord_config = DiscordConfig(
        bot_token=discord_secrets.get("bot_token", ""),
        guild_id=discord_secrets.get("guild_id", ""),
        health_channel_id=discord_secrets.get("health_channel_id", ""),
        poll_interval=int(os.getenv("POLL_INTERVAL", "30")),
        message_window_minutes=int(os.getenv("MESSAGE_WINDOW_MINUTES", "30")),
    )

    # LLM config
    llm_config = LLMConfig(
        api_key=anthropic_secrets.get("api_key", ""),
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    )

    # Database config
    database_config = DatabaseConfig(
        connection_string=db_connection_string,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    )

    # Ollama config
    ollama_config = OllamaConfig(
        base_url=ollama_secrets.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
        model=os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
        embedding_dim=int(os.getenv("OLLAMA_EMBEDDING_DIM", "768")),
    )

    # Main config
    config = Config(
        discord=discord_config,
        llm=llm_config,
        database=database_config,
        ollama=ollama_config,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        run_once=os.getenv("RUN_ONCE", "false").lower() == "true",
    )

    # Validate configuration
    if not config.validate():
        raise ValueError("Invalid configuration - check logs for details")

    return config


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from httpx and other libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
