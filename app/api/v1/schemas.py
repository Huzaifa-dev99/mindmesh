from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class IndexRequest(BaseModel):
    chunk_size: int | None = Field(default=None, ge=1)
    chunk_overlap: int | None = Field(default=None, ge=0)
    document_ids: list[str] = Field(default_factory=list)


class IndexedDocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunk_count: int
    point_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class IndexResponse(BaseModel):
    source: str
    indexed_documents: int
    indexed_chunks: int
    skipped_documents: int
    documents: list[IndexedDocumentResponse] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    score_threshold: float | None = Field(default=None, ge=0)
    session_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    retrieval_enabled: bool = True
    web_search_enabled: bool = True
    route_mode: str | None = None
    model: str | None = None


class SourceResponse(BaseModel):
    source: str
    score: float | None = None
    vector_id: str | None = None
    collection_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    session_id: str | None = None
    interaction_id: str | None = None
    query: str
    contextualized_query: str | None = None
    route: str | None = None
    route_reasoning: str | None = None
    answer: str
    context_count: int
    sources: list[SourceResponse] = Field(default_factory=list)


class DocumentRegistryResponse(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)
    skipped: list[dict[str, Any]] = Field(default_factory=list)


class DocumentIdsRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1)


class DocumentActionResponse(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)
    removed_documents: int = 0
    removed_vectors: int = 0


class ChatSessionsResponse(BaseModel):
    sessions: list[dict[str, Any]] = Field(default_factory=list)


class ChatInteractionsResponse(BaseModel):
    interactions: list[dict[str, Any]] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    totals: dict[str, Any] = Field(default_factory=dict)
    document_status: list[dict[str, Any]] = Field(default_factory=list)
    document_tags: list[dict[str, Any]] = Field(default_factory=list)
    document_versions: list[dict[str, Any]] = Field(default_factory=list)
    top_referenced_documents: list[dict[str, Any]] = Field(default_factory=list)
    recent_queries: list[dict[str, Any]] = Field(default_factory=list)
    recent_failed_documents: list[dict[str, Any]] = Field(default_factory=list)
    storage: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)


class AIKeyCreateRequest(BaseModel):
    provider: str
    label: str
    api_key: str = Field(min_length=1)
    base_url: str | None = None


class AISettingsUpdateRequest(BaseModel):
    provider: str
    key_id: str | None = None
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)


class AIAdminResponse(BaseModel):
    providers: list[str] = Field(default_factory=list)
    default_base_urls: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    keys: list[dict[str, Any]] = Field(default_factory=list)


class AIModelsResponse(BaseModel):
    provider: str
    models: list[str] = Field(default_factory=list)


class PromptUpdateRequest(BaseModel):
    content: str = Field(min_length=1)
    change_note: str | None = None


class PromptsResponse(BaseModel):
    prompts: list[dict[str, Any]] = Field(default_factory=list)


class PromptResponse(BaseModel):
    prompt: dict[str, Any] = Field(default_factory=dict)
