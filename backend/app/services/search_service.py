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
        points = []
        source_types = set(request.source_types or [])
        include_all = not source_types
        notes_vector_service = VectorService(settings.QDRANT_NOTES_COLLECTION)

        if include_all or "journal" in source_types:
            journal_filter = models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="journal")),
                ]
            )
            points.extend(await notes_vector_service.search(vector, request.limit, journal_filter))

        if include_all or "note" in source_types:
            note_must = [
                models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                models.FieldCondition(key="source_type", match=models.MatchValue(value="note")),
                models.FieldCondition(key="scope", match=models.MatchValue(value="global")),
            ]
            if request.tags:
                note_must.append(models.FieldCondition(key="tags", match=models.MatchAny(any=request.tags)))
            points.extend(await notes_vector_service.search(vector, request.limit, models.Filter(must=note_must)))

        if include_all or "document" in source_types:
            document_filter = models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                    models.FieldCondition(key="scope", match=models.MatchValue(value="global")),
                ]
            )
            points.extend(await VectorService(settings.QDRANT_DOCUMENTS_COLLECTION).search(vector, request.limit, document_filter))
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
