from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))
    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    journals = relationship("JournalTag", back_populates="tag", cascade="all, delete-orphan")
    notes = relationship("NoteTag", back_populates="tag", cascade="all, delete-orphan")
