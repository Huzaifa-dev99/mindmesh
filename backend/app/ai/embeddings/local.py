import asyncio
import logging

from fastembed import TextEmbedding

from app.ai.providers.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = TextEmbedding(model_name=self.model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def _embed() -> list[list[float]]:
            return [vector.tolist() for vector in self._model.embed(texts)]

        return await asyncio.to_thread(_embed)
