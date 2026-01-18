"""External connections for Oura Health Agent."""

from externalconnections.fetch_secrets import (
    get_discord_secrets,
    get_anthropic_secrets,
    get_database_secrets,
    get_ollama_secrets,
)

__all__ = [
    "get_discord_secrets",
    "get_anthropic_secrets",
    "get_database_secrets",
    "get_ollama_secrets",
]
