import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)
    source_types: list[Literal["journal", "note"]] | None = None
    tags: list[str] | None = None


class SearchResult(BaseModel):
    source_type: str
    source_id: uuid.UUID
    score: float
    title: str | None = None
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
