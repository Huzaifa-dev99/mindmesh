import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from qdrant_client.http import models

from app.ai.embeddings.chunking import chunk_text
from app.ai.embeddings.local import FastEmbedProvider
from app.core.config import settings
from app.services.vector_service import VectorService


class DocumentService:
    def __init__(self) -> None:
        self.embedding_provider = FastEmbedProvider()
        self.vector_service = VectorService(settings.QDRANT_DOCUMENTS_COLLECTION)

    async def upload_and_ingest(self, user_id: uuid.UUID, file_name: str, content: str, file_type: str = "text/plain") -> dict:
        if not content.strip():
            raise HTTPException(status_code=400, detail="Uploaded document has no indexable text")

        document_id = uuid.uuid4()
        safe_name = Path(file_name or f"{document_id}.txt").name
        object_path = f"{settings.MINIO_BUCKET}/{user_id}/{document_id}/{safe_name}"
        target = Path(settings.MINIO_DATA_PATH) / object_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        chunks = chunk_text(content)
        if not chunks:
            raise HTTPException(status_code=400, detail="No indexable text found in document")
        vectors = await self.embedding_provider.embed(chunks)
        uploaded_at = datetime.now(timezone.utc).isoformat()
        payloads = [
            {
                "source_type": "document",
                "user_id": str(user_id),
                "document_id": str(document_id),
                "source_id": str(document_id),
                "file_name": safe_name,
                "file_type": file_type,
                "chunk_id": str(uuid.uuid4()),
                "chunk_index": index,
                "uploaded_date": uploaded_at,
                "minio_object_path": object_path,
                "title": safe_name,
                "text": chunk,
            }
            for index, chunk in enumerate(chunks)
        ]
        await self.vector_service.upsert(vectors, payloads)
        return {
            "document_id": document_id,
            "file_name": safe_name,
            "file_type": file_type,
            "uploaded_date": uploaded_at,
            "minio_object_path": object_path,
            "chunk_count": len(chunks),
        }

    async def list_documents(self, user_id: uuid.UUID) -> list[dict]:
        points = await self.vector_service.scroll(
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                ]
            ),
            limit=500,
        )
        documents: dict[str, dict] = {}
        for point in points:
            payload = point.payload or {}
            document_id = payload.get("document_id") or payload.get("source_id")
            if not document_id:
                continue
            entry = documents.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "file_name": payload.get("file_name") or payload.get("title") or "Untitled document",
                    "file_type": payload.get("file_type"),
                    "uploaded_date": payload.get("uploaded_date"),
                    "minio_object_path": payload.get("minio_object_path"),
                    "chunk_count": 0,
                },
            )
            entry["chunk_count"] += 1
        return sorted(documents.values(), key=lambda item: item.get("uploaded_date") or "", reverse=True)

    async def delete_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        documents = await self.list_documents(user_id)
        document = next((item for item in documents if str(item["document_id"]) == str(document_id)), None)
        await self.vector_service.delete_source(user_id, "document", document_id)
        if document and document.get("minio_object_path"):
            target = Path(settings.MINIO_DATA_PATH) / document["minio_object_path"]
            if target.exists():
                target.unlink()
