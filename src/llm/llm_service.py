import asyncio
import logging
import time

from core.abstract_service import AbstractService
from core.bus import EventBus
from core.events import AIMessage, LLMInputMessage
from llm.agent.graph import graph
from llm.agent.utils import llm_input_to_langchain

logger = logging.getLogger("llm")


class LLMService(AbstractService):
    def __init__(self, bus: EventBus):
        super().__init__(bus)

        self.queue = asyncio.Queue()
        bus.subscribe(LLMInputMessage, self.queue)

    async def run(self):
        """
        Runs the LLM service.
        """
        while True:
            event = await self.queue.get()

            start_time = time.time()
            response = await asyncio.to_thread(
                graph.invoke,
                {
                    "metadata": event.metadata,
                    "user_name": event.user_name,
                    "messages": [llm_input_to_langchain(event)],
                    "retry_count": 0,
                    "parsed_messages": [],
                },
                config={"configurable": {"thread_id": "default"}},
            )
            end_time = time.time()
            latency = end_time - start_time
            logger.info(f"Total AI Agent Latency: {latency}")

            parsed_messages = response.get("parsed_messages", [])
            if not parsed_messages:
                logger.error(
                    "Graph completed without parsed messages, skipping publish"
                )
                continue

            for content in parsed_messages:
                await self.bus.publish(
                    AIMessage(content=content, metadata=response["metadata"])
                )
