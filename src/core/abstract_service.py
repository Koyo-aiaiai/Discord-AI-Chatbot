from abc import ABC, abstractmethod

from core.bus import EventBus


class AbstractService(ABC):
    def __init__(self, bus: EventBus):
        self.bus = bus

    @abstractmethod
    async def run(self):
        """
        Runs the service.
        """
        raise NotImplementedError()