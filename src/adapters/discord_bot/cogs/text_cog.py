from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List

import discord
from discord.ext import commands

from adapters.discord_bot.bot import DiscordBot
from adapters.discord_bot.data import DiscordMessage

DISCORD_TYPING_WAIT_TIMER = 3
DISCORD_TYPING_TIMEOUT_TIMER = 10.2

logger = logging.getLogger("adapter")


class DiscordTextCog(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.messages_to_send: List[discord.Message] = []

        self.active_user_typing: dict[int, bool] = {}
        self.user_typing_timers: dict[int, asyncio.Task] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Listen for messages in any channel that the bot can see. Sends messages to the Discord service."""
        if message.author == self.bot.user:
            return

        if not message.content or self.bot.service is None:
            return

        self.messages_to_send.append(message)
        self.active_user_typing[message.author.id] = False

        # If the user doesn't type within the next 3 seconds, the messages are sent to the next service in line
        await asyncio.sleep(DISCORD_TYPING_WAIT_TIMER)
        if self.active_user_typing[message.author.id]:
            return
        typing_task = self.user_typing_timers.get(message.author.id)
        typing_task.cancel()

        if not self.messages_to_send:
            return
        # Concatenates all content from messages since last interaction.
        # Does not take into account if there are mutliple authors.
        content = ""
        for message in self.messages_to_send:
            content += f"{message.content}\n"

        ai_messages = await self.get_ai_messages_batch(message.channel)

        message = DiscordMessage(
            content=content,
            author=message.author,
            channel=message.channel,
            ai_messages=ai_messages,
            created_at=datetime.now(),
        )
        await self.bot.service.handle_discord_message(message)
        self.messages_to_send = []

    @commands.Cog.listener()
    async def on_typing(
        self, channel: discord.TextChannel, user: discord.User, when: datetime
    ) -> None:
        """Sees if the user is still typing in a channel. If the user has not stopped for past DISCORD_TYPING_WAIT_TIMER seconds, contrinue blocking message sending."""
        self.active_user_typing[user.id] = True
        typing_task = self.user_typing_timers.get(user.id)
        if typing_task:
            typing_task.cancel()
        self.user_typing_timers[user.id] = asyncio.create_task(
            self._check_typing_no_message_sent(user, channel)
        )

        # NOTE: This currently does not support conversations on multiple channels at the same time
        if user.bot or self.bot.service is None:
            return

    # TODO: Currently the user parameter does nothing, in future this should probably support multiple users
    async def _check_typing_no_message_sent(
        self, user: discord.User, channel: discord.TextChannel
    ):
        try:
            # This block is for if the user does not send a message but stops typing
            # Sends all messages in the messages_to_send to the behavioural service
            await asyncio.sleep(DISCORD_TYPING_TIMEOUT_TIMER)
            if not self.messages_to_send:
                return

            content = ""
            for message in self.messages_to_send:
                content += f"{message.content}\n"

            ai_messages = await self.get_ai_messages_batch(channel)

            message = DiscordMessage(
                content=content,
                author=message.author,
                channel=message.channel,
                ai_messages=ai_messages,
                created_at=datetime.now(),
            )
            await self.bot.service.handle_discord_message(message)
            self.messages_to_send = []

        except asyncio.CancelledError:
            # User continued typing before the DISCORD_TYPING_TIMEOUT_TIMER seconds is up
            return

    async def get_ai_messages_batch(self, channel):
        batches = []

        # Iterate from newest to oldest
        # iterate through all newest user messages without adding to batches
        # iterate through all recent AI messages in the last block and add to batches
        # upon seeing a user (not the bot) we break
        async for msg in channel.history(limit=30):
            if msg.author.id == self.bot.user.id:
                batches.append(msg)
            elif not batches:
                continue
            else:
                break

        batches.reverse()
        return batches


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(DiscordTextCog(bot))
