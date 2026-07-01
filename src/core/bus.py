import asyncio
import logging

logger = logging.getLogger("core")


class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, queue: asyncio.Queue):
        self.subscribers.setdefault(event_type, []).append(queue)

    async def publish(self, event):
        logger.debug(f"Publishing event: {event}")
        event_type = type(event)

        if event_type not in self.subscribers:
            logger.warning(f"No subscribers for event type: {event_type}")
            return

        for queue in self.subscribers.get(event_type, []):
            await queue.put(event)
