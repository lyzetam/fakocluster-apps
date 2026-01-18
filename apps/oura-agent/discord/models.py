"""Discord data models for Oura Health Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any


class EmbedColor(IntEnum):
    """Discord embed colors for health-related responses."""

    EXCELLENT = 0x57F287  # Green - scores 85+
    GOOD = 0x3498DB  # Blue - scores 70-84
    FAIR = 0xFEE75C  # Yellow - scores 50-69
    POOR = 0xE74C3C  # Red - scores below 50
    INFO = 0x99AAB5  # Gray - neutral info
    ERROR = 0xED4245  # Red - error state


@dataclass
class DiscordMessage:
    """Represents a Discord message."""

    id: str
    content: str
    author_id: str
    author_username: str
    author_bot: bool
    channel_id: str
    timestamp: datetime
    reactions: list[dict] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> "DiscordMessage":
        """Create from Discord API response."""
        author = data.get("author", {})
        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            author_id=author.get("id", ""),
            author_username=author.get("username", "unknown"),
            author_bot=author.get("bot", False),
            channel_id=data.get("channel_id", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat()).replace("Z", "+00:00")
            ),
            reactions=data.get("reactions", []),
        )

    def has_reaction(self, emoji: str, from_bot: bool = True) -> bool:
        """Check if message has a specific reaction.

        Args:
            emoji: Emoji to check for
            from_bot: If True, only count reactions from the bot

        Returns:
            bool: True if reaction exists
        """
        for reaction in self.reactions:
            reaction_emoji = reaction.get("emoji", {})
            emoji_name = reaction_emoji.get("name", "")
            if emoji_name == emoji:
                if from_bot and reaction.get("me", False):
                    return True
                elif not from_bot:
                    return True
        return False


@dataclass
class DiscordEmbed:
    """Represents a Discord embed."""

    title: str
    description: str
    color: int = EmbedColor.INFO

    footer_text: str | None = None
    timestamp: datetime | None = None
    fields: list[dict] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Discord API format."""
        embed = {
            "title": self.title,
            "description": self.description[:4096],  # Discord limit
            "color": self.color,
        }

        if self.footer_text:
            embed["footer"] = {"text": self.footer_text}

        if self.timestamp:
            embed["timestamp"] = self.timestamp.isoformat()

        if self.fields:
            embed["fields"] = self.fields[:25]  # Discord limit

        return embed


def get_health_embed_color(score: float | None = None) -> int:
    """Get embed color based on health score.

    Args:
        score: Health score (0-100) or None for neutral

    Returns:
        int: Discord color code
    """
    if score is None:
        return EmbedColor.INFO

    if score >= 85:
        return EmbedColor.EXCELLENT
    elif score >= 70:
        return EmbedColor.GOOD
    elif score >= 50:
        return EmbedColor.FAIR
    else:
        return EmbedColor.POOR


def create_health_embed(
    title: str,
    description: str,
    score: float | None = None,
    fields: list[dict] | None = None,
) -> DiscordEmbed:
    """Create a health-themed embed.

    Args:
        title: Embed title
        description: Main content
        score: Optional health score for color coding
        fields: Optional embed fields

    Returns:
        DiscordEmbed: Configured embed
    """
    color = get_health_embed_color(score)

    return DiscordEmbed(
        title=f"Oura Health | {title}",
        description=description,
        color=color,
        footer_text=f"Oura Health Agent | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        fields=fields,
    )
