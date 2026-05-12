import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.chunking import chunk_text
from app.ai.embeddings.local import FastEmbedProvider
from app.ai.prompts.templates import SUMMARY_PROMPT
from app.ai.providers.groq import GroqChatProvider
from app.models.embedding import EmbeddingMetadata
from app.models.journal import Journal
from app.models.note import Note
from app.repositories.content_repository import (
    EmbeddingRepository,
    JournalRepository,
    NoteRepository,
    TagRepository,
)
from app.schemas.journal import JournalCreate, JournalResponse, JournalSummary, JournalUpdate
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.schemas.tag import TagResponse
from app.services.vector_service import VectorService


def journal_to_response(journal: Journal) -> JournalResponse:
    return JournalResponse(
        id=journal.id,
        user_id=journal.user_id,
        title=journal.title,
        content=journal.content,
        mood=journal.mood,
        tags=[link.tag.name for link in journal.tags],
        metadata=journal.metadata_,
        is_private=journal.is_private,
        created_at=journal.created_at,
        updated_at=journal.updated_at,
    )


def note_to_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        user_id=note.user_id,
        title=note.title,
        content=note.content,
        source=note.source,
        tags=[link.tag.name for link in note.tags],
        metadata=note.metadata_,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.embedding_provider = FastEmbedProvider()
        self.vector_service = VectorService()
        self.embedding_repository = EmbeddingRepository(session)

    async def reindex(
        self,
        user_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        title: str | None,
        content: str,
        tags: list[str],
        metadata: dict,
    ) -> None:
        await self.vector_service.delete_source(user_id, source_type, source_id)
        chunks = chunk_text(content)
        if not chunks:
            return
        vectors = await self.embedding_provider.embed(chunks)
        payloads = [
            {
                "user_id": str(user_id),
                "source_type": source_type,
                "source_id": str(source_id),
                "title": title,
                "chunk_index": index,
                "text": chunk,
                "tags": tags,
                **metadata,
            }
            for index, chunk in enumerate(chunks)
        ]
        point_ids = await self.vector_service.upsert(vectors, payloads)
        rows = [
            EmbeddingMetadata(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                qdrant_point_id=point_id,
                chunk_index=index,
                chunk_text=chunk,
                embedding_model=self.embedding_provider.model_name,
                metadata_=payloads[index],
            )
            for index, (point_id, chunk) in enumerate(zip(point_ids, chunks))
        ]
        await self.embedding_repository.replace_for_source(user_id, source_type, source_id, rows)


class JournalService:
    def __init__(self, session: AsyncSession):
        self.journals = JournalRepository(session)
        self.tags = TagRepository(session)
        self.ingestion = IngestionService(session)
        self.ai = GroqChatProvider()

    async def list_journals(self, user_id: uuid.UUID) -> list[JournalResponse]:
        return [journal_to_response(item) for item in await self.journals.list_for_user(user_id)]

    async def create_journal(self, user_id: uuid.UUID, data: JournalCreate) -> JournalResponse:
        tags = await self.tags.get_or_create_many(user_id, data.tags)
        journal = await self.journals.create(user_id, data, tags)
        response = journal_to_response(journal)
        await self.ingestion.reindex(
            user_id, "journal", journal.id, journal.title, journal.content, response.tags, journal.metadata_
        )
        return response

    async def update_journal(
        self, journal_id: uuid.UUID, user_id: uuid.UUID, data: JournalUpdate
    ) -> JournalResponse:
        journal = await self.journals.get_by_id(journal_id, user_id)
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        tags = await self.tags.get_or_create_many(user_id, data.tags) if data.tags is not None else None
        updated = await self.journals.update(journal, data, tags)
        response = journal_to_response(updated)
        await self.ingestion.reindex(
            user_id, "journal", updated.id, updated.title, updated.content, response.tags, updated.metadata_
        )
        return response

    async def delete_journal(self, journal_id: uuid.UUID, user_id: uuid.UUID) -> None:
        journal = await self.journals.get_by_id(journal_id, user_id)
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        await self.journals.soft_delete(journal)
        await self.ingestion.vector_service.delete_source(user_id, "journal", journal.id)

    async def summarize(self, journal_id: uuid.UUID, user_id: uuid.UUID) -> JournalSummary:
        journal = await self.journals.get_by_id(journal_id, user_id)
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        summary = await self.ai.complete(
            [{"role": "user", "content": SUMMARY_PROMPT.format(content=journal.content)}]
        )
        return JournalSummary(summary=summary)


class NoteService:
    def __init__(self, session: AsyncSession):
        self.notes = NoteRepository(session)
        self.tags = TagRepository(session)
        self.ingestion = IngestionService(session)

    async def list_notes(self, user_id: uuid.UUID) -> list[NoteResponse]:
        return [note_to_response(item) for item in await self.notes.list_for_user(user_id)]

    async def create_note(self, user_id: uuid.UUID, data: NoteCreate) -> NoteResponse:
        tags = await self.tags.get_or_create_many(user_id, data.tags)
        note = await self.notes.create(user_id, data, tags)
        response = note_to_response(note)
        await self.ingestion.reindex(user_id, "note", note.id, note.title, note.content, response.tags, note.metadata_)
        return response

    async def update_note(self, note_id: uuid.UUID, user_id: uuid.UUID, data: NoteUpdate) -> NoteResponse:
        note = await self.notes.get_by_id(note_id, user_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        tags = await self.tags.get_or_create_many(user_id, data.tags) if data.tags is not None else None
        updated = await self.notes.update(note, data, tags)
        response = note_to_response(updated)
        await self.ingestion.reindex(
            user_id, "note", updated.id, updated.title, updated.content, response.tags, updated.metadata_
        )
        return response

    async def delete_note(self, note_id: uuid.UUID, user_id: uuid.UUID) -> None:
        note = await self.notes.get_by_id(note_id, user_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        await self.notes.soft_delete(note)
        await self.ingestion.vector_service.delete_source(user_id, "note", note.id)

    async def list_tags(self, user_id: uuid.UUID) -> list[TagResponse]:
        return [TagResponse.model_validate(tag) for tag in await self.tags.list_for_user(user_id)]
