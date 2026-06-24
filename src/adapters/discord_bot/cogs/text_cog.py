from __future__ import annotations

import discord
from discord.ext import commands

from adapters.discord_bot.bot import DiscordBot


class DiscordTextCog(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Listen for messages in any channel that the bot can see. Sends messages to the Discord service."""
        if message.author == self.bot.user:
            return

        if not message.content or self.bot.service is None:
            return

        await self.bot.service.handle_discord_message(message)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(DiscordTextCog(bot))
