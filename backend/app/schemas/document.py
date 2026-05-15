from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    document_id: UUID | str
    file_name: str
    file_type: str | None = None
    uploaded_date: datetime | str | None = None
    minio_object_path: str
    chunk_count: int = 0
    scope: str = "global"
    chat_id: UUID | str | None = None
    status: str = "indexed"
    requires_multimodal: bool = False


class DocumentUpload(BaseModel):
    file_name: str
    content: str | None = None
    file_type: str = "text/plain"
    scope: str = "global"
    chat_id: UUID | None = None
    selected_model_id: str | None = None
    selected_model_supports_vision: bool = False


class DocumentScopeUpdate(BaseModel):
    scope: str
    chat_id: UUID | None = None
