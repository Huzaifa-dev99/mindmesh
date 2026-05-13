import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic import ConfigDict

from app.schemas.search import SearchResult


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    use_rag: bool = True
    limit: int = Field(5, ge=1, le=5)
    tavily_api_key: str | None = Field(None, max_length=255)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    citations: list[SearchResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
