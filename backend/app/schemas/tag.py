import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    color: str | None = Field(None, max_length=20)


class TagResponse(TagCreate, ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
