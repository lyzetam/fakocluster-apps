"""Discord API client for Oura Health Agent."""

import logging
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from discord.models import DiscordEmbed, DiscordMessage, EmbedColor, create_health_embed

logger = logging.getLogger(__name__)


class DiscordClient:
    """Async Discord client for bot operations.

    Handles:
    - Fetching messages from the health channel
    - Sending messages with health-themed embeds
    - Adding reactions to mark messages as processed
    """

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, token: str, processed_emoji: str = "\U0001FA7A"):
        """Initialize the Discord client.

        Args:
            token: Discord bot token
            processed_emoji: Emoji to mark processed messages (default: 🩺)
        """
        if not token:
            raise ValueError("Discord bot token is required")

        self.token = token
        self.processed_emoji = processed_emoji
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

    async def fetch_messages(
        self, channel_id: str, limit: int = 20
    ) -> list[DiscordMessage]:
        """Fetch recent messages from a channel.

        Args:
            channel_id: Discord channel ID
            limit: Max messages to fetch

        Returns:
            List of DiscordMessage objects
        """
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"
        params = {"limit": limit}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            messages = []
            for msg_data in response.json():
                messages.append(DiscordMessage.from_api(msg_data))

            return messages

    async def filter_new_messages(
        self,
        messages: list[DiscordMessage],
        window_minutes: int = 30,
    ) -> list[DiscordMessage]:
        """Filter messages to only new, unprocessed ones.

        Args:
            messages: List of messages to filter
            window_minutes: Only include messages from last N minutes

        Returns:
            Filtered list of messages
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        logger.debug(f"Filtering {len(messages)} messages (cutoff: {cutoff})")

        filtered = []
        for msg in messages:
            # Skip bot messages
            if msg.author_bot:
                logger.debug(f"Skipping bot message: {msg.id}")
                continue

            # Skip old messages
            msg_time = (
                msg.timestamp.replace(tzinfo=timezone.utc)
                if msg.timestamp.tzinfo is None
                else msg.timestamp
            )
            if msg_time < cutoff:
                logger.debug(f"Skipping old message: {msg.id} from {msg_time}")
                continue

            # Skip already processed (has our reaction)
            if msg.has_reaction(self.processed_emoji, from_bot=True):
                logger.debug(f"Skipping processed message: {msg.id}")
                continue

            # Skip empty messages
            if not msg.content.strip():
                logger.debug(f"Skipping empty message: {msg.id}")
                continue

            logger.info(f"New message from {msg.author_username}: {msg.content[:50]}")
            filtered.append(msg)

        return filtered

    async def send_message(
        self,
        channel_id: str,
        content: str | None = None,
        embed: DiscordEmbed | None = None,
        mention_user_id: str | None = None,
    ) -> dict:
        """Send a message to a channel.

        Args:
            channel_id: Discord channel ID
            content: Message text content
            embed: Optional embed
            mention_user_id: User ID to mention

        Returns:
            API response dict
        """
        url = f"{self.BASE_URL}/channels/{channel_id}/messages"

        # Build mention
        mention = f"<@{mention_user_id}>" if mention_user_id else ""

        payload = {}

        if content or mention:
            payload["content"] = f"{mention} {content or ''}".strip()

        if embed:
            payload["embeds"] = [embed.to_dict()]

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_health_response(
        self,
        channel_id: str,
        user_id: str,
        response_text: str,
        title: str = "Health Insight",
        score: float | None = None,
    ) -> dict:
        """Send a formatted health response with color-coded embed.

        Args:
            channel_id: Discord channel ID
            user_id: User to mention
            response_text: Agent's response text
            title: Embed title (default: "Health Insight")
            score: Optional health score for color coding

        Returns:
            API response dict
        """
        # Truncate if too long
        if len(response_text) > 4000:
            response_text = response_text[:3900] + "\n\n_[Response truncated]_"

        embed = create_health_embed(
            title=title,
            description=response_text,
            score=score,
        )

        return await self.send_message(
            channel_id=channel_id,
            embed=embed,
            mention_user_id=user_id,
        )

    async def send_error_response(
        self,
        channel_id: str,
        user_id: str,
        error_message: str,
    ) -> dict:
        """Send an error response.

        Args:
            channel_id: Discord channel ID
            user_id: User to mention
            error_message: Error description

        Returns:
            API response dict
        """
        embed = DiscordEmbed(
            title="Oura Health | Error",
            description=f"I encountered an issue while processing your request:\n\n{error_message}\n\nPlease try again or rephrase your question.",
            color=EmbedColor.ERROR,
            footer_text=f"Oura Health Agent | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )

        return await self.send_message(
            channel_id=channel_id,
            embed=embed,
            mention_user_id=user_id,
        )

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Add a reaction to a message.

        Args:
            channel_id: Discord channel ID
            message_id: Message ID to react to
            emoji: Emoji to add

        Returns:
            True if successful
        """
        encoded_emoji = urllib.parse.quote(emoji)
        url = f"{self.BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"

        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers)
            # 204 No Content = success
            return response.status_code in (200, 204)

    async def mark_as_processed(
        self,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """Mark a message as processed with the health emoji.

        Args:
            channel_id: Discord channel ID
            message_id: Message ID

        Returns:
            True if successful
        """
        return await self.add_reaction(
            channel_id=channel_id,
            message_id=message_id,
            emoji=self.processed_emoji,
        )

    async def test_connection(self) -> bool:
        """Test the Discord connection by fetching bot info.

        Returns:
            True if connection successful
        """
        url = f"{self.BASE_URL}/users/@me"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                bot_info = response.json()
                logger.info(f"Connected as {bot_info.get('username')}#{bot_info.get('discriminator')}")
                return True
        except Exception as e:
            logger.error(f"Discord connection test failed: {e}")
            return False
