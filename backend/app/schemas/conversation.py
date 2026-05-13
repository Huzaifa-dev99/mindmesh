import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import MessageResponse


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime | None
    message_count: int = 0
    last_message_at: datetime | None = None


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse] = Field(default_factory=list)


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
