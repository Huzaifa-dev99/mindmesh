import uuid

from qdrant_client.http import models

from app.ai.embeddings.local import FastEmbedProvider
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.vector_service import VectorService


class SearchService:
    def __init__(self) -> None:
        self.embedding_provider = FastEmbedProvider()
        self.vector_service = VectorService()

    async def search(self, user_id: uuid.UUID, request: SearchRequest) -> SearchResponse:
        vector = (await self.embedding_provider.embed([request.query]))[0]
        must = [models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))]
        if request.source_types:
            must.append(models.FieldCondition(key="source_type", match=models.MatchAny(any=request.source_types)))
        if request.tags:
            must.append(models.FieldCondition(key="tags", match=models.MatchAny(any=request.tags)))
        points = await self.vector_service.search(vector, request.limit, models.Filter(must=must))
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
