import asyncio
import logging

from adapters.discord_bot.discord_service import DiscordService
from behaviour.behaviour_service import BehaviourService
from core.bus import EventBus
from llm.llm_service import LLMService


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

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
