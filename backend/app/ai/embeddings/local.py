import asyncio
import hashlib
import logging
import math
import re

from app.ai.providers.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)
_FASTEMBED_UNAVAILABLE = False
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = None
        if not _FASTEMBED_UNAVAILABLE:
            self._model = self._load_model()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            return hash_embed_texts(texts, self.dimension)

        def _embed() -> list[list[float]]:
            return [vector.tolist() for vector in self._model.embed(texts)]

        try:
            return await asyncio.to_thread(_embed)
        except Exception:
            self._disable_fastembed("fastembed_embedding_failed")
            return hash_embed_texts(texts, self.dimension)

    def _load_model(self):
        try:
            from fastembed import TextEmbedding

            return TextEmbedding(model_name=self.model_name)
        except Exception:
            self._disable_fastembed("fastembed_model_unavailable")
            return None

    def _disable_fastembed(self, reason: str) -> None:
        global _FASTEMBED_UNAVAILABLE
        _FASTEMBED_UNAVAILABLE = True
        self._model = None
        logger.warning("%s model=%s fallback=hashing", reason, self.model_name, exc_info=True)


def hash_embed_texts(texts: list[str], dimension: int) -> list[list[float]]:
    return [hash_embed_text(text, dimension) for text in texts]


def hash_embed_text(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    tokens = _TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        tokens = [text.lower() or "empty"]

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]
