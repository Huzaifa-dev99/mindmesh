import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.schemas.ai_settings import AIModelResponse


@dataclass
class StoredAIConfig:
    provider: str
    api_key: str
    default_model_id: str | None = None
    is_verified: bool = False
    verified_at: datetime | None = None
    models: list[AIModelResponse] = field(default_factory=list)


_USER_CONFIGS: dict[str, StoredAIConfig] = {}
_CHAT_MODELS: dict[str, tuple[str, str]] = {}


class AISettingsService:
    providers = ["OpenAI", "Gemini", "Claude", "Groq"]

    async def save_config(
        self,
        user_id: uuid.UUID,
        provider: str,
        api_key: str,
        default_model_id: str | None = None,
    ) -> StoredAIConfig:
        normalized_provider = normalize_provider(provider)
        models = await self.list_models_for_key(normalized_provider, api_key)
        config = StoredAIConfig(
            provider=normalized_provider,
            api_key=api_key,
            default_model_id=default_model_id or (models[0].id if models else None),
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
            models=models,
        )
        _USER_CONFIGS[str(user_id)] = config
        return config

    def get_config(self, user_id: uuid.UUID) -> StoredAIConfig | None:
        config = _USER_CONFIGS.get(str(user_id))
        if config:
            return config
        if settings.GROQ_API_KEY:
            return StoredAIConfig(
                provider="Groq",
                api_key=settings.GROQ_API_KEY,
                default_model_id="llama-3.1-8b-instant",
                is_verified=True,
                verified_at=None,
                models=static_models("Groq"),
            )
        return None

    async def list_models(self, user_id: uuid.UUID, provider: str | None = None) -> list[AIModelResponse]:
        config = self.get_config(user_id)
        if config and (provider is None or normalize_provider(provider) == config.provider):
            return config.models or static_models(config.provider)
        return static_models(normalize_provider(provider or "Groq"))

    async def list_models_for_key(self, provider: str, api_key: str) -> list[AIModelResponse]:
        if provider == "Groq":
            ids = await fetch_openai_compatible_models("https://api.groq.com/openai/v1/models", api_key)
            return [model_from_id("Groq", model_id) for model_id in ids] or static_models("Groq")
        if provider == "OpenAI":
            ids = await fetch_openai_compatible_models("https://api.openai.com/v1/models", api_key)
            chat_ids = [item for item in ids if item.startswith(("gpt-", "o", "chatgpt-"))]
            return [model_from_id("OpenAI", model_id) for model_id in chat_ids] or static_models("OpenAI")
        if provider == "Gemini":
            ids = await fetch_gemini_models(api_key)
            return [model_from_id("Gemini", model_id) for model_id in ids] or static_models("Gemini")
        if provider == "Claude":
            ids = await fetch_claude_models(api_key)
            return [model_from_id("Claude", model_id) for model_id in ids] or static_models("Claude")
        return static_models(provider)

    def set_chat_model(self, user_id: uuid.UUID, conversation_id: uuid.UUID, provider: str, model_id: str) -> tuple[str, str]:
        selected = (normalize_provider(provider), model_id)
        _CHAT_MODELS[f"{user_id}:{conversation_id}"] = selected
        return selected

    def get_chat_model(self, user_id: uuid.UUID, conversation_id: uuid.UUID | None) -> tuple[str | None, str | None]:
        if conversation_id:
            selected = _CHAT_MODELS.get(f"{user_id}:{conversation_id}")
            if selected:
                return selected
        config = self.get_config(user_id)
        if config:
            return config.provider, config.default_model_id
        return None, None

    def get_api_key(self, user_id: uuid.UUID, provider: str | None = None) -> str | None:
        config = self.get_config(user_id)
        if config and (provider is None or normalize_provider(provider) == config.provider):
            return config.api_key
        return None


async def fetch_openai_compatible_models(url: str, api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        payload = response.json()
    return sorted(item["id"] for item in payload.get("data", []) if isinstance(item, dict) and item.get("id"))


async def fetch_gemini_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": api_key})
        response.raise_for_status()
        payload = response.json()
    return sorted((item.get("name", "").removeprefix("models/") for item in payload.get("models", [])), key=str.lower)


async def fetch_claude_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )
        response.raise_for_status()
        payload = response.json()
    return sorted(item["id"] for item in payload.get("data", []) if isinstance(item, dict) and item.get("id"))


def normalize_provider(provider: str) -> str:
    match = provider.strip().lower()
    if match == "openai":
        return "OpenAI"
    if match == "gemini":
        return "Gemini"
    if match in {"anthropic", "claude"}:
        return "Claude"
    return "Groq"


def model_from_id(provider: str, model_id: str) -> AIModelResponse:
    lowered = model_id.lower()
    capabilities: list[str] = []
    if any(token in lowered for token in ["reason", "o1", "o3", "o4", "r1"]):
        capabilities.append("Reasoning")
    if "mini" in lowered or "8b" in lowered or "instant" in lowered:
        capabilities.extend(["Mini", "Fast"])
    if any(token in lowered for token in ["vision", "gpt-4o", "llava", "vl", "gemini"]):
        capabilities.extend(["Multimodal", "Vision"])
    if any(token in lowered for token in ["mixtral", "moe"]):
        capabilities.append("MoE")
    if any(token in lowered for token in ["code", "coder"]):
        capabilities.append("Coding")
    if not capabilities:
        capabilities.append("General")
    unique_capabilities = list(dict.fromkeys(capabilities))
    return AIModelResponse(
        id=model_id,
        provider=provider,
        name=model_id,
        display_name=model_id,
        capabilities=unique_capabilities,
        supports_text=True,
        supports_vision="Vision" in unique_capabilities or "Multimodal" in unique_capabilities,
        supports_documents=True,
    )


def static_models(provider: str) -> list[AIModelResponse]:
    catalog = {
        "Groq": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llava-v1.5-7b-4096-preview"],
        "OpenAI": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "o4-mini"],
        "Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        "Claude": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
    }
    return [model_from_id(provider, model_id) for model_id in catalog.get(provider, catalog["Groq"])]
