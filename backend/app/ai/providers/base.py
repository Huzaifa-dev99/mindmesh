from abc import ABC, abstractmethod


class ChatProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    model_name: str
    dimension: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
