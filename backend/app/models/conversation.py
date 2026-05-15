from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_created", "user_id", "created_at"),)

    title: Mapped[str | None] = mapped_column(String(255))
    archived_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    conversation_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )

    conversation = relationship("Conversation", back_populates="messages")
