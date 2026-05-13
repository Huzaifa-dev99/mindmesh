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


class DocumentUpload(BaseModel):
    file_name: str
    content: str
    file_type: str = "text/plain"
