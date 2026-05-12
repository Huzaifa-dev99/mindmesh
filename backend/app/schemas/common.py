import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Timestamped(ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None


class StatusResponse(BaseModel):
    status: str
    detail: str | None = None
    services: dict[str, Any] | None = None
