from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Journal(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "journals"
    __table_args__ = (Index("ix_journals_user_created", "user_id", "created_at"),)

    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str | None] = mapped_column(String(50))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    user = relationship("User", back_populates="journals")
    tags = relationship("JournalTag", back_populates="journal", cascade="all, delete-orphan")


class JournalTag(Base):
    __tablename__ = "journal_tags"

    journal_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id"), primary_key=True
    )
    tag_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)

    journal = relationship("Journal", back_populates="tags")
    tag = relationship("Tag", back_populates="journals")
