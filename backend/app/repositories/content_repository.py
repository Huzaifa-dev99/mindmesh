import uuid

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.embedding import EmbeddingMetadata
from app.models.journal import Journal, JournalTag
from app.models.note import Note, NoteTag
from app.models.tag import Tag
from app.schemas.journal import JournalCreate, JournalUpdate
from app.schemas.note import NoteCreate, NoteUpdate


class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_many(self, user_id: uuid.UUID, names: list[str]) -> list[Tag]:
        tags: list[Tag] = []
        for raw_name in {name.strip().lower() for name in names if name.strip()}:
            result = await self.session.execute(
                select(Tag).where(Tag.user_id == user_id, Tag.name == raw_name, Tag.deleted_at.is_(None))
            )
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(user_id=user_id, name=raw_name)
                self.session.add(tag)
                await self.session.flush()
            tags.append(tag)
        return tags

    async def list_for_user(self, user_id: uuid.UUID) -> list[Tag]:
        result = await self.session.execute(
            select(Tag).where(Tag.user_id == user_id, Tag.deleted_at.is_(None)).order_by(Tag.name)
        )
        return list(result.scalars().all())


class JournalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, journal_id: uuid.UUID, user_id: uuid.UUID) -> Journal | None:
        result = await self.session.execute(
            select(Journal)
            .options(selectinload(Journal.tags).selectinload(JournalTag.tag))
            .where(Journal.id == journal_id, Journal.user_id == user_id, Journal.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[Journal]:
        result = await self.session.execute(
            select(Journal)
            .options(selectinload(Journal.tags).selectinload(JournalTag.tag))
            .where(Journal.user_id == user_id, Journal.deleted_at.is_(None))
            .order_by(desc(Journal.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, data: JournalCreate, tags: list[Tag]) -> Journal:
        journal = Journal(
            user_id=user_id,
            title=data.title,
            content=data.content,
            mood=data.mood,
            metadata_=data.metadata,
            is_private=data.is_private,
        )
        self.session.add(journal)
        await self.session.flush()
        self.session.add_all([JournalTag(journal_id=journal.id, tag_id=tag.id) for tag in tags])
        await self.session.flush()
        return await self.get_by_id(journal.id, user_id) or journal

    async def update(self, journal: Journal, data: JournalUpdate, tags: list[Tag] | None) -> Journal:
        values = data.model_dump(exclude_unset=True, exclude={"tags", "metadata"})
        for key, value in values.items():
            setattr(journal, key, value)
        if data.metadata is not None:
            journal.metadata_ = data.metadata
        if tags is not None:
            await self.session.execute(delete(JournalTag).where(JournalTag.journal_id == journal.id))
            self.session.add_all([JournalTag(journal_id=journal.id, tag_id=tag.id) for tag in tags])
        await self.session.flush()
        return await self.get_by_id(journal.id, journal.user_id) or journal

    async def soft_delete(self, journal: Journal) -> None:
        from sqlalchemy import func

        journal.deleted_at = func.now()
        await self.session.flush()


class NoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
        result = await self.session.execute(
            select(Note)
            .options(selectinload(Note.tags).selectinload(NoteTag.tag))
            .where(Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[Note]:
        result = await self.session.execute(
            select(Note)
            .options(selectinload(Note.tags).selectinload(NoteTag.tag))
            .where(Note.user_id == user_id, Note.deleted_at.is_(None))
            .order_by(desc(Note.updated_at), desc(Note.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, user_id: uuid.UUID, data: NoteCreate, tags: list[Tag]) -> Note:
        note = Note(
            user_id=user_id,
            title=data.title,
            content=data.content,
            source=data.source,
            scope="chat" if data.scope == "chat" else "global",
            chat_id=data.chat_id if data.scope == "chat" else None,
            metadata_=data.metadata,
        )
        self.session.add(note)
        await self.session.flush()
        self.session.add_all([NoteTag(note_id=note.id, tag_id=tag.id) for tag in tags])
        await self.session.flush()
        return await self.get_by_id(note.id, user_id) or note

    async def update(self, note: Note, data: NoteUpdate, tags: list[Tag] | None) -> Note:
        values = data.model_dump(exclude_unset=True, exclude={"tags", "metadata"})
        for key, value in values.items():
            setattr(note, key, value)
        if data.metadata is not None:
            note.metadata_ = data.metadata
        if tags is not None:
            await self.session.execute(delete(NoteTag).where(NoteTag.note_id == note.id))
            self.session.add_all([NoteTag(note_id=note.id, tag_id=tag.id) for tag in tags])
        await self.session.flush()
        return await self.get_by_id(note.id, note.user_id) or note

    async def soft_delete(self, note: Note) -> None:
        from sqlalchemy import func

        note.deleted_at = func.now()
        await self.session.flush()


class EmbeddingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def replace_for_source(
        self,
        user_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        rows: list[EmbeddingMetadata],
    ) -> None:
        await self.session.execute(
            delete(EmbeddingMetadata).where(
                EmbeddingMetadata.user_id == user_id,
                EmbeddingMetadata.source_type == source_type,
                EmbeddingMetadata.source_id == source_id,
            )
        )
        self.session.add_all(rows)
        await self.session.flush()
