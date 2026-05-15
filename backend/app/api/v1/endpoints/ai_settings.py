import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai_settings import (
    AIModelResponse,
    AIProviderConfigRequest,
    AIProviderConfigResponse,
    ChatModelRequest,
    ChatModelResponse,
)
from app.services.ai_settings_service import AISettingsService

router = APIRouter()


@router.get("/providers", response_model=list[str])
async def providers():
    return AISettingsService.providers


@router.get("/config", response_model=AIProviderConfigResponse | None)
async def get_config(current_user: User = Depends(get_current_user)):
    config = AISettingsService().get_config(current_user.id)
    if config is None:
        return None
    return AIProviderConfigResponse(
        provider=config.provider,
        has_api_key=True,
        is_verified=config.is_verified,
        verified_at=config.verified_at,
        default_model_id=config.default_model_id,
        models=config.models,
    )


@router.post("/config", response_model=AIProviderConfigResponse)
async def save_config(payload: AIProviderConfigRequest, current_user: User = Depends(get_current_user)):
    try:
        config = await AISettingsService().save_config(
            current_user.id,
            payload.provider,
            payload.api_key,
            payload.default_model_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not verify API key: {exc}") from exc
    return AIProviderConfigResponse(
        provider=config.provider,
        has_api_key=True,
        is_verified=config.is_verified,
        verified_at=config.verified_at,
        default_model_id=config.default_model_id,
        models=config.models,
    )


@router.get("/models", response_model=list[AIModelResponse])
async def models(provider: str | None = None, current_user: User = Depends(get_current_user)):
    return await AISettingsService().list_models(current_user.id, provider)


@router.get("/chats/{conversation_id}/model", response_model=ChatModelResponse)
async def get_chat_model(conversation_id: uuid.UUID, current_user: User = Depends(get_current_user)):
    provider, model_id = AISettingsService().get_chat_model(current_user.id, conversation_id)
    return ChatModelResponse(provider=provider, model_id=model_id)


@router.patch("/chats/{conversation_id}/model", response_model=ChatModelResponse)
async def set_chat_model(
    conversation_id: uuid.UUID,
    payload: ChatModelRequest,
    current_user: User = Depends(get_current_user),
):
    provider, model_id = AISettingsService().set_chat_model(
        current_user.id,
        conversation_id,
        payload.provider,
        payload.model_id,
    )
    return ChatModelResponse(provider=provider, model_id=model_id)
