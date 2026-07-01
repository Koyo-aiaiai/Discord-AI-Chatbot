import asyncio
from typing import List

from behaviour.turn_control.turn_control import TurnControl
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
        self.turn_control = TurnControl()

        self.messages_to_send: str = ""

    async def run(self) -> None:
        """
        Runs the behaviour service.
        """
        while True:
            event = await self.queue.get()

            self.messages_to_send += f"\n {event.content}"

            if self.turn_control.check_is_respond_turn(event):
                llm_input_message = LLMInputMessage(
                    content=self.messages_to_send,
                    user_name=event.user_name,
                    metadata=event.metadata,
                )
                await self.bus.publish(llm_input_message)
            else:
                # Turn control says that it is not yet AI's turn to respond
                # Store message until get signal that it is actually AI's turn to respond
                # FIXME: this kinda sits here forever if the the turn control is ever wrong
                continue
