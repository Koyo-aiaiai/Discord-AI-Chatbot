import asyncio

from core.abstract_service import AbstractService
from core.bus import EventBus
from core.events import LLMInputMessage, UserMessage


class BehaviourService(AbstractService):
    """
    Service for the behaviour component.
    Communication between the platform (like discord and stuff) and the AI
    Listens for UserMessages and publishes LLMInputMessages
    """
    def __init__(self, bus: EventBus):
        super().__init__(bus)

        self.queue: asyncio.Queue[UserMessage] = asyncio.Queue()
        bus.subscribe(UserMessage, self.queue)

    async def run(self) -> None:
        """
        Runs the behaviour service.
        """
        while True:
            event = await self.queue.get()

            llm_input_message = LLMInputMessage(
                content=event.content,
                user_name=event.user_name,
                metadata=event.metadata,
            )
            await self.bus.publish(llm_input_message)