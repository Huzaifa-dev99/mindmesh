import uuid

import pytest

from app.core.config import settings
from app.ai.embeddings.local import hash_embed_texts
from app.services.document_service import DocumentService, extract_document_text


def test_extract_text_document_bytes():
    content = extract_document_text("notes.txt", "text/plain", b"alpha beta")

    assert content == "alpha beta"


def test_extract_binary_document_has_safe_placeholder():
    content = extract_document_text(
        "deck.ppt",
        "application/vnd.ms-powerpoint",
        b"binary",
    )

    assert "deck.ppt" in content
    assert "Text extraction is not available" in content


def test_hash_embedding_fallback_is_deterministic_and_sized():
    first = hash_embed_texts(["alpha beta"], 384)[0]
    second = hash_embed_texts(["alpha beta"], 384)[0]

    assert first == second
    assert len(first) == 384
    assert any(value != 0 for value in first)


@pytest.mark.asyncio
async def test_upload_and_ingest_supports_global_and_chat_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MINIO_DATA_PATH", str(tmp_path))
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    vector_service = FakeVectorService()
    service = DocumentService(vector_service=vector_service, embedding_provider=FakeEmbeddingProvider())

    global_document = await service.upload_and_ingest(
        user_id,
        "global.txt",
        file_bytes=b"global upload content",
        file_type="text/plain",
        scope="global",
    )
    chat_document = await service.upload_and_ingest(
        user_id,
        "chat.txt",
        file_bytes=b"chat upload content",
        file_type="text/plain",
        scope="chat",
        chat_id=chat_id,
    )

    assert global_document["scope"] == "global"
    assert global_document["status"] == "indexed"
    assert chat_document["scope"] == "chat"
    assert chat_document["chat_id"] == chat_id
    assert chat_document["status"] == "indexed"
    assert len(vector_service.payloads) == 2
    assert {payload["scope"] for payload in vector_service.payloads} == {"global", "chat"}
    assert all((tmp_path / payload["minio_object_path"]).exists() for payload in vector_service.payloads)


class FakeEmbeddingProvider:
    async def embed(self, texts):
        return [[1.0, *([0.0] * 383)] for _ in texts]


class FakeVectorService:
    def __init__(self):
        self.payloads = []

    async def upsert(self, vectors, payloads):
        self.payloads.extend(payloads)
        return [str(uuid.uuid4()) for _ in vectors]
