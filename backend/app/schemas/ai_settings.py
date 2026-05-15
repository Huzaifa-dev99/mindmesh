from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AIModelResponse(BaseModel):
    id: str
    provider: str
    name: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    supports_text: bool = True
    supports_vision: bool = False
    supports_documents: bool = True


class AIProviderConfigRequest(BaseModel):
    provider: str
    api_key: str = Field(..., min_length=1, max_length=4096)
    default_model_id: str | None = None


class AIProviderConfigResponse(BaseModel):
    provider: str
    has_api_key: bool
    is_verified: bool
    verified_at: datetime | None = None
    default_model_id: str | None = None
    models: list[AIModelResponse] = Field(default_factory=list)


class ChatModelRequest(BaseModel):
    provider: str
    model_id: str


class ChatModelResponse(BaseModel):
    provider: str | None = None
    model_id: str | None = None


ProviderName = Literal["OpenAI", "Gemini", "Claude", "Groq"]
