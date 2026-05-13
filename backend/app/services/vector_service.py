import uuid
from typing import Any

from qdrant_client.http import models

from app.core.config import settings
from app.db.qdrant import ensure_collection, qdrant_client


class VectorService:
    def __init__(self, collection_name: str | None = None) -> None:
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        ensure_collection(self.collection_name)

    async def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        point_ids: list[str] | None = None,
    ) -> list[str]:
        ids = point_ids or [str(uuid.uuid4()) for _ in vectors]
        points = [
            models.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        qdrant_client.upsert(collection_name=self.collection_name, points=points)
        return ids

    async def search(
        self,
        vector: list[float],
        limit: int,
        filters: models.Filter | None = None,
    ):
        if hasattr(qdrant_client, "search"):
            return qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=filters,
                limit=limit,
                with_payload=True,
            )
        response = qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=filters,
            limit=limit,
            with_payload=True,
        )
        return response.points

    async def delete_source(self, user_id: uuid.UUID, source_type: str, source_id: uuid.UUID) -> None:
        qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                        models.FieldCondition(key="source_type", match=models.MatchValue(value=source_type)),
                        models.FieldCondition(key="source_id", match=models.MatchValue(value=str(source_id))),
                    ]
                )
            ),
        )

    async def scroll(self, filters: models.Filter, limit: int = 100):
        points, _ = qdrant_client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filters,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return points
