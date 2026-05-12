from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class EmbeddingMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "embeddings_metadata"
    __table_args__ = (
        Index("ix_embeddings_owner_source", "user_id", "source_type", "source_id"),
        Index("ix_embeddings_qdrant_point", "qdrant_point_id"),
    )

    user_id: Mapped[object] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[object] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    qdrant_point_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
