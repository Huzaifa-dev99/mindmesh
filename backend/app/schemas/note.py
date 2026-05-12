import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class NoteBase(BaseModel):
    title: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1)
    source: str | None = Field(None, max_length=255)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    content: str | None = Field(None, min_length=1)
    source: str | None = Field(None, max_length=255)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class NoteResponse(NoteBase, ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
