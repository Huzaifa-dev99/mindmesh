from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Note(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (Index("ix_notes_user_updated", "user_id", "updated_at"),)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    user = relationship("User", back_populates="notes")
    tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("notes.id"), primary_key=True)
    tag_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)

    note = relationship("Note", back_populates="tags")
    tag = relationship("Tag", back_populates="notes")
