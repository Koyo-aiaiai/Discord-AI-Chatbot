from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord


class MockDiscordPlatform:
    """
    In-memory stand-in for Discord DMs.

    Builds fake discord.py message objects for inbound traffic and records
    outbound sends without connecting to the gateway.
    """

    def __init__(
        self,
        user_id: int = 111_222_333,
        channel_id: int = 444_555_666,
        username: str = "testuser",
    ):
        self.user_id = user_id
        self.channel_id = channel_id
        self.username = username
        self.sent_messages: list[dict[str, Any]] = []

    def _make_channel(self) -> MagicMock:
        channel = MagicMock()
        channel.__class__ = discord.DMChannel
        channel.id = self.channel_id
        channel.recipient = MagicMock(id=self.user_id)
        channel.send = AsyncMock(side_effect=self._capture_send)
        return channel

    async def _capture_send(self, content: str) -> None:
        self.sent_messages.append(
            {"channel_id": str(self.channel_id), "content": content}
        )

    def incoming_dm(
        self,
        content: str,
        *,
        created_at: datetime | None = None,
    ) -> MagicMock:
        """Build a fake inbound DM as discord.py would deliver to on_message."""
        author = MagicMock()
        author.id = self.user_id
        author.name = self.username

        message = MagicMock()
        message.content = content
        message.author = author
        message.channel = self._make_channel()
        message.created_at = created_at or datetime.now(timezone.utc)
        return message

    def attach_bot(self, service: Any):
        """
        Attach a DiscordBot to the service whose send_to_channel writes to
        sent_messages instead of calling the real API.
        """
        from adapters.discord_bot.bot import DiscordBot

        channel = self._make_channel()
        bot = DiscordBot(service=service)
        bot.get_channel = MagicMock(return_value=channel)
        bot.fetch_channel = AsyncMock(return_value=channel)
        service.bot = bot
        return bot
