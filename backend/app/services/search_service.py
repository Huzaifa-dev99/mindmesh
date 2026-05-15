import uuid

from qdrant_client.http import models

from app.ai.embeddings.local import FastEmbedProvider
from app.core.config import settings
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.vector_service import VectorService


class SearchService:
    def __init__(self) -> None:
        self.embedding_provider = FastEmbedProvider()

    async def search(self, user_id: uuid.UUID, request: SearchRequest) -> SearchResponse:
        vector = (await self.embedding_provider.embed([request.query]))[0]
        collections = []
        if not request.source_types or any(item in {"note", "journal"} for item in request.source_types):
            collections.append(settings.QDRANT_NOTES_COLLECTION)
        if not request.source_types or "document" in request.source_types:
            collections.append(settings.QDRANT_DOCUMENTS_COLLECTION)

        points = []
        for collection in collections:
            must = [models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))]
            if request.source_types:
                source_types = [item for item in request.source_types if item != "document"] if collection == settings.QDRANT_NOTES_COLLECTION else ["document"]
                must.append(models.FieldCondition(key="source_type", match=models.MatchAny(any=source_types)))
            elif collection == settings.QDRANT_DOCUMENTS_COLLECTION:
                must.append(models.FieldCondition(key="scope", match=models.MatchValue(value="global")))
            if request.source_types and collection == settings.QDRANT_DOCUMENTS_COLLECTION:
                must.append(models.FieldCondition(key="scope", match=models.MatchValue(value="global")))
            if request.tags and collection == settings.QDRANT_NOTES_COLLECTION:
                must.append(models.FieldCondition(key="tags", match=models.MatchAny(any=request.tags)))
            points.extend(await VectorService(collection).search(vector, request.limit, models.Filter(must=must)))
        points = sorted(points, key=lambda point: point.score, reverse=True)[: request.limit]
        results = [
            SearchResult(
                source_type=point.payload.get("source_type"),
                source_id=uuid.UUID(point.payload.get("source_id")),
                score=point.score,
                title=point.payload.get("title"),
                snippet=point.payload.get("text", ""),
                metadata={k: v for k, v in point.payload.items() if k not in {"text"}},
            )
            for point in points
        ]
        return SearchResponse(query=request.query, results=results)
