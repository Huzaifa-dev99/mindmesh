from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AIProviderConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_provider_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_ai_provider_configs_user"),)

    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    default_model_id: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    models: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    user = relationship("User")


class ChatModelSelection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_model_selections"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", name="uq_chat_model_selection_user_conversation"),
        Index("ix_chat_model_selection_user_conversation", "user_id", "conversation_id"),
    )

    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    conversation_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)

    user = relationship("User")
    conversation = relationship("Conversation")
