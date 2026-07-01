import asyncio

from adapters.discord_bot.discord_service import DiscordService
from behaviour.behaviour_service import BehaviourService
from core.bus import EventBus
from llm.llm_service import LLMService
from logging_config import setup_logging


async def run() -> None:
    setup_logging()

    bus = EventBus()

    discord_service = DiscordService(bus)
    behaviour_service = BehaviourService(bus)
    llm_service = LLMService(bus)

    await asyncio.gather(
        discord_service.run(),
        behaviour_service.run(),
        llm_service.run(),
    )


if __name__ == "__main__":
    asyncio.run(run())
