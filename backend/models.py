"""Fast API models definition"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# JSON input schema
class InputData(BaseModel):
    id: str
    type: str  # "text", "image", "url", etc.
    content_raw: str  # actual input or path to file
    source: str  # "upload", "web", etc.
    tags: Optional[List[str]] = []
    timestamp: Optional[datetime] = None