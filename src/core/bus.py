import asyncio
import logging

from constants import ANSI

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, queue: asyncio.Queue):
        self.subscribers.setdefault(event_type, []).append(queue)

    async def publish(self, event):
        logger.debug(f"{ANSI['CORE_DEBUG_COLOUR']}Publishing event: {event}{ANSI['ANSI_RESET']}")
        event_type = type(event)

        if event_type not in self.subscribers:
            logger.warning(f"{ANSI['CORE_DEBUG_COLOUR']}No subscribers for event type: {event_type}{ANSI['ANSI_RESET']}")
            return

        for queue in self.subscribers.get(event_type, []):
            await queue.put(event)