# Defines the basic operations every automation surface should provide.

from abc import ABC, abstractmethod

from src.models.action import BrowserAction


class Surface(ABC):

    @abstractmethod
    async def open(self):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def observe(self) -> dict:
        pass

    @abstractmethod
    async def act(self, action: BrowserAction):
        pass

    @abstractmethod
    async def screenshot(self, file_path: str):
        pass