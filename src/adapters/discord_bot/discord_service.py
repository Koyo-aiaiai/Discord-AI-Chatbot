import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from dotenv import load_dotenv

from adapters.discord_bot.bot import DiscordBot
from adapters.discord_bot.data import DiscordMessage
from constants import ANSI
from core.abstract_service import AbstractService
from core.bus import EventBus
from core.events import AIMessage, MessageMetaData, UserMessage

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class DiscordService(AbstractService):
    """
    Service for the discord platform.
    Entry and Exit point for the communication between AI and user through Discord.
    Listens for AIMessage and publishes UserMessage.
    """

    def __init__(self, bus: EventBus):
        super().__init__(bus)

        self.queue: asyncio.Queue[AIMessage] = asyncio.Queue()
        bus.subscribe(AIMessage, self.queue)
        self.bot: DiscordBot | None = None
        self._last_message_at: dict[str, dict[str, datetime]] = {}

    def _get_channel_times(self, channel_id: str) -> dict[str, datetime]:
        return self._last_message_at.setdefault(channel_id, {})

    @staticmethod
    def _elapsed_since(last_at: datetime | None, now: datetime) -> timedelta:
        if last_at is None:
            return timedelta(0)
        return now - last_at

    def _build_user_metadata(
        self,
        channel_id: str,
        user_id: str,
        platform_type: str,
        now: datetime,
    ) -> MessageMetaData:
        times = self._get_channel_times(channel_id)
        return MessageMetaData(
            platform_type=platform_type,
            user_id=user_id,
            channel_id=channel_id,
            timestamp=now,
            tslr_user_ai=self._elapsed_since(times.get("ai"), now),
            tslr_ai_user=self._elapsed_since(times.get("user"), now),
            tslr_ai_ai=self._elapsed_since(times.get("ai"), now),
        )

    def _record_user_message(self, channel_id: str, now: datetime) -> None:
        self._get_channel_times(channel_id)["user"] = now

    def _record_ai_message(self, channel_id: str, now: datetime) -> None:
        self._get_channel_times(channel_id)["ai"] = now

    async def handle_discord_message(self, message: DiscordMessage) -> None:
        """Pack a Discord message as a UserMessage and publish it to the event bus."""

        now = message.created_at
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        platform_type = "discord_text"

        user_message = UserMessage(
            content=message.content,
            user_name=str(message.author.name),
            metadata=self._build_user_metadata(channel_id, user_id, platform_type, now),
        )
        self._record_user_message(channel_id, now)

        if self.bot is not None:
            self.bot.channels[channel_id] = message.channel

        logger.info(
            f"{ANSI['PLATFORM_DEBUG_COLOUR']}Publishing UserMessage from user {user_id}{ANSI['ANSI_RESET']}"
        )
        await self.bus.publish(user_message)

    async def _process_ai_messages(self) -> None:
        while True:
            ai_message = await self.queue.get()
            if self.bot is None:
                logger.warning(
                    "Received AIMessage before Discord bot was ready, dropping"
                )
                continue

            channel_id = ai_message.metadata.channel_id
            logger.info(
                f"{ANSI['PLATFORM_DEBUG_COLOUR']}Sending AIMessage to channel {channel_id}{ANSI['ANSI_RESET']}"
            )
            await self.bot.send_to_channel(ai_message.content, channel_id)
            self._record_ai_message(channel_id, datetime.now(timezone.utc))

    @staticmethod
    def _load_token() -> str:
        load_dotenv(_PROJECT_ROOT / ".env")
        token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError(
                "Discord token not set. Add DISCORD_BOT_TOKEN or DISCORD_TOKEN to .env at the project root."
            )
        return token

    async def run(self) -> None:
        """Run the Discord bot and forward bus events to Discord."""
        token = self._load_token()
        self.bot = DiscordBot(service=self)

        await asyncio.gather(
            self._process_ai_messages(),
            self.bot.start(token),
        )
