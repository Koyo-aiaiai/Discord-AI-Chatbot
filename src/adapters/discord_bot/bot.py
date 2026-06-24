from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from constants import ANSI

if TYPE_CHECKING:
    from adapters.discord_bot.discord_service import DiscordService

logger = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    def __init__(self, service: DiscordService | None = None):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.service = service
        self.channels: dict[str, discord.TextChannel] = {}

    async def setup_hook(self) -> None:
        await self.load_extension("adapters.discord_bot.cogs.text_cog")

    async def on_ready(self) -> None:
        logger.info("Discord bot logged in as %s", self.user)

    async def send_to_channel(self, content: str, channel_id: str) -> None:
        """Send a message to the Discord channel identified by channel_id."""
        channel = self.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await self.fetch_channel(int(channel_id))
            except discord.NotFound:
                logger.error(
                    f"{ANSI['PLATFORM_DEBUG_COLOUR']}Discord channel {channel_id} not found{ANSI['ANSI_RESET']}"
                )
                return

        if isinstance(channel, discord.DMChannel):
            self.dm_channels[channel.recipient.id] = channel
        elif isinstance(channel, discord.TextChannel):
            self.channels[channel.id] = channel

        if isinstance(channel, discord.DMChannel):
            async with channel.typing():
                await asyncio.sleep(len(content) / 15)
                await channel.send(content)
        elif isinstance(channel, discord.TextChannel):
            async with channel.typing():
                await asyncio.sleep(len(content) / 15)
                await channel.send(content)
