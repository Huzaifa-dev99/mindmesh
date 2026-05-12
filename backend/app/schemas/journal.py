import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class JournalBase(BaseModel):
    title: str | None = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    mood: str | None = Field(None, max_length=50)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_private: bool = True


class JournalCreate(JournalBase):
    pass


class JournalUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    content: str | None = Field(None, min_length=1)
    mood: str | None = Field(None, max_length=50)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    is_private: bool | None = None


class JournalResponse(JournalBase, ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None


class JournalSummary(BaseModel):
    summary: str
    insights: list[str] = Field(default_factory=list)
