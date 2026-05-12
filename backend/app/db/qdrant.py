import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings

logger = logging.getLogger(__name__)

qdrant_client = QdrantClient(url=settings.QDRANT_URL, check_compatibility=False)


def ensure_collection() -> None:
    collections = qdrant_client.get_collections().collections
    if any(collection.name == settings.QDRANT_COLLECTION for collection in collections):
        return
    qdrant_client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=settings.EMBEDDING_DIMENSION,
            distance=models.Distance.COSINE,
        ),
    )
    logger.info("qdrant_collection_created collection=%s", settings.QDRANT_COLLECTION)


def check_qdrant_connection() -> bool:
    try:
        qdrant_client.get_collections()
        return True
    except Exception:
        logger.exception("qdrant_health_check_failed")
        return False
