from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.v1.schemas import (
    AIAdminResponse,
    AIKeyCreateRequest,
    AIModelsResponse,
    AISettingsUpdateRequest,
    ChatInteractionsResponse,
    ChatSessionUpdateRequest,
    ChatSessionsResponse,
    DashboardResponse,
    DocumentActionResponse,
    DocumentIdsRequest,
    DocumentRegistryResponse,
    DocumentUploadResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    IndexRequest,
    IndexResponse,
    PromptResponse,
    PromptsResponse,
    PromptUpdateRequest,
    UserPinRequest,
    UserPinVerifyResponse,
    UserProfileRequest,
    UserStateResponse,
)
from app.core.config import (
    APP_NAME,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    RETRIEVER_SCORE_THRESHOLD,
    RETRIEVER_TOP_K,
)
from app.core.logging import get_logger, trace
from app.core.storage import SUPPORTED_DOCUMENT_EXTENSIONS
from app.services.document_registry import list_documents
from app.services.chat_history import delete_session, list_interactions, list_sessions, update_session

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    logger.debug("health check requested")
    return HealthResponse(status="ok", service=APP_NAME)


@router.get("/user", response_model=UserStateResponse)
def user_state_endpoint() -> UserStateResponse:
    trace("User state requested", logger)
    try:
        from app.services.users import get_user_state

        return UserStateResponse(**get_user_state())
    except Exception as exc:
        logger.exception("User state failed")
        raise HTTPException(status_code=500, detail="User state failed") from exc


@router.put("/user/profile", response_model=UserStateResponse)
def update_user_profile_endpoint(request: UserProfileRequest) -> UserStateResponse:
    trace("User profile update requested", logger)
    try:
        from app.services.users import update_user_profile

        return UserStateResponse(
            **update_user_profile(
                name=request.name,
                avatar=request.avatar,
                bio=request.bio,
                nicknames=request.nicknames,
                highlight_color=request.highlight_color,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("User profile update failed")
        raise HTTPException(status_code=500, detail="User profile update failed") from exc


@router.put("/user/pin", response_model=UserStateResponse)
def set_user_pin_endpoint(request: UserPinRequest) -> UserStateResponse:
    trace("User PIN set requested", logger)
    try:
        from app.services.users import set_user_pin

        return UserStateResponse(**set_user_pin(request.pin))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("User PIN set failed")
        raise HTTPException(status_code=500, detail="User PIN set failed") from exc


@router.post("/user/pin/reset", response_model=UserStateResponse)
def reset_user_pin_endpoint(request: UserPinRequest) -> UserStateResponse:
    trace("User PIN reset requested", logger)
    try:
        from app.services.users import set_user_pin

        return UserStateResponse(**set_user_pin(request.pin))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("User PIN reset failed")
        raise HTTPException(status_code=500, detail="User PIN reset failed") from exc


@router.post("/user/pin/verify", response_model=UserPinVerifyResponse)
def verify_user_pin_endpoint(request: UserPinRequest) -> UserPinVerifyResponse:
    trace("User PIN verification requested", logger)
    try:
        from app.services.users import verify_user_pin

        return UserPinVerifyResponse(**verify_user_pin(request.pin), unlocked=True)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("User PIN verification failed")
        raise HTTPException(status_code=500, detail="User PIN verification failed") from exc


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard_endpoint() -> DashboardResponse:
    trace("Dashboard analytics requested", logger)
    try:
        from app.services.analytics import dashboard_analytics

        return DashboardResponse(**dashboard_analytics())
    except Exception as exc:
        logger.exception("Dashboard analytics failed")
        raise HTTPException(status_code=500, detail="Dashboard analytics failed") from exc


@router.get("/admin/ai", response_model=AIAdminResponse)
def ai_admin_endpoint() -> AIAdminResponse:
    trace("AI admin state requested", logger)
    try:
        from app.services.ai_settings import get_ai_admin_state

        return AIAdminResponse(**get_ai_admin_state())
    except Exception as exc:
        logger.exception("AI admin state failed")
        raise HTTPException(status_code=500, detail="AI admin state failed") from exc


@router.post("/admin/ai/keys", response_model=AIAdminResponse)
def add_ai_key_endpoint(request: AIKeyCreateRequest) -> AIAdminResponse:
    trace(f"AI key creation requested for provider {request.provider}", logger)
    try:
        from app.services.ai_settings import add_provider_key, get_ai_admin_state

        add_provider_key(
            provider=request.provider,
            label=request.label,
            api_key=request.api_key,
            base_url=request.base_url,
        )
        return AIAdminResponse(**get_ai_admin_state())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI key creation failed")
        raise HTTPException(status_code=500, detail="AI key creation failed") from exc


@router.delete("/admin/ai/keys/{key_id}", response_model=AIAdminResponse)
def delete_ai_key_endpoint(key_id: str) -> AIAdminResponse:
    trace("AI key deletion requested", logger)
    try:
        from app.services.ai_settings import delete_provider_key, get_ai_admin_state

        delete_provider_key(key_id)
        return AIAdminResponse(**get_ai_admin_state())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI key deletion failed")
        raise HTTPException(status_code=500, detail="AI key deletion failed") from exc


@router.put("/admin/ai/settings", response_model=AIAdminResponse)
def update_ai_settings_endpoint(request: AISettingsUpdateRequest) -> AIAdminResponse:
    trace(f"AI settings update requested for provider {request.provider}", logger)
    try:
        from app.services.ai_settings import get_ai_admin_state, update_ai_settings

        update_ai_settings(
            provider=request.provider,
            key_id=request.key_id,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return AIAdminResponse(**get_ai_admin_state())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI settings update failed")
        raise HTTPException(status_code=500, detail="AI settings update failed") from exc


@router.get("/admin/ai/models", response_model=AIModelsResponse)
def ai_models_endpoint(provider: str, key_id: str | None = None) -> AIModelsResponse:
    trace(f"AI model listing requested for provider {provider}", logger)
    try:
        from app.services.ai_settings import list_provider_models

        models = list_provider_models(provider=provider, key_id=key_id)
        return AIModelsResponse(provider=provider, models=models)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI model listing failed")
        raise HTTPException(
            status_code=502,
            detail="AI model listing failed. Check provider base URL and API key.",
        ) from exc


@router.get("/admin/prompts", response_model=PromptsResponse)
def prompts_endpoint() -> PromptsResponse:
    trace("Prompt listing requested", logger)
    try:
        from app.services.prompts import list_prompts

        return PromptsResponse(prompts=list_prompts())
    except Exception as exc:
        logger.exception("Prompt listing failed")
        raise HTTPException(status_code=500, detail="Prompt listing failed") from exc


@router.put("/admin/prompts/{prompt_name}", response_model=PromptResponse)
def update_prompt_endpoint(
    prompt_name: str,
    request: PromptUpdateRequest,
) -> PromptResponse:
    trace(f"Prompt update requested for {prompt_name}", logger)
    try:
        from app.services.prompts import update_prompt

        return PromptResponse(
            prompt=update_prompt(
                prompt_name,
                content=request.content,
                change_note=request.change_note,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prompt update failed")
        raise HTTPException(status_code=500, detail="Prompt update failed") from exc


@router.post("/index", response_model=IndexResponse)
def index_endpoint(request: IndexRequest) -> IndexResponse:
    trace("Document indexing requested", logger)
    try:
        from app.services.indexing import index_documents

        result = index_documents(
            chunk_size=request.chunk_size or CHUNK_SIZE,
            chunk_overlap=(
                request.chunk_overlap
                if request.chunk_overlap is not None
                else CHUNK_OVERLAP
            ),
            show_progress=False,
            document_ids=request.document_ids or None,
        )
        return IndexResponse(
            source=result.source,
            indexed_documents=result.indexed_documents,
            indexed_chunks=result.indexed_chunks,
            skipped_documents=result.skipped_documents,
            documents=[document.__dict__ for document in result.documents],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Indexing failed")
        raise HTTPException(status_code=500, detail="Indexing failed") from exc


@router.post("/generate", response_model=GenerateResponse)
def generate_endpoint(request: GenerateRequest) -> GenerateResponse:
    trace("Generation requested", logger)
    try:
        from app.services.generation import answer_question

        history = list_interactions(request.session_id) if request.session_id else []
        result = answer_question(
            request.query,
            history=history,
            top_k=request.top_k or RETRIEVER_TOP_K,
            score_threshold=(
                request.score_threshold
                if request.score_threshold is not None
                else RETRIEVER_SCORE_THRESHOLD
            ),
            session_id=request.session_id,
            document_ids=request.document_ids,
            tags=request.tags,
            retrieval_enabled=request.retrieval_enabled,
            web_search_enabled=request.web_search_enabled,
            route_mode=request.route_mode,
            model=request.model,
        )
        return GenerateResponse(
            session_id=result.session_id,
            interaction_id=result.interaction_id,
            query=result.query,
            contextualized_query=result.contextualized_query,
            route=result.route,
            route_reasoning=result.route_reasoning,
            answer=result.answer,
            context_count=len(result.contexts),
            sources=result.sources,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail="Generation failed") from exc


@router.get("/documents", response_model=DocumentRegistryResponse)
def documents_endpoint() -> DocumentRegistryResponse:
    trace("Document registry requested", logger)
    return DocumentRegistryResponse(documents=list_documents())


@router.post("/documents/sync", response_model=DocumentRegistryResponse)
def sync_documents_endpoint() -> DocumentRegistryResponse:
    trace("Document storage sync requested", logger)
    try:
        from app.services.document_storage import sync_storage_documents

        return DocumentRegistryResponse(documents=sync_storage_documents())
    except Exception as exc:
        logger.exception("Document sync failed")
        raise HTTPException(status_code=500, detail="Document sync failed") from exc


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_documents_endpoint(
    files: list[UploadFile] = File(...),
    filenames: list[str] = Form(...),
    tags: list[str] = Form(...),
) -> DocumentUploadResponse:
    trace(f"Document upload requested for {len(files)} file(s)", logger)
    try:
        from app.services.document_storage import (
            UploadCandidate,
            parse_tags,
            upload_documents,
        )

        if len(files) != len(filenames) or len(files) != len(tags):
            raise ValueError("Each uploaded file must include filename and tags metadata.")

        payload = []
        allowed_extensions = set(SUPPORTED_DOCUMENT_EXTENSIONS)
        for index, file in enumerate(files):
            original_filename = file.filename or ""
            content = await file.read()
            extension = "." + original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
            if extension not in allowed_extensions:
                supported = ", ".join(sorted(allowed_extensions))
                raise ValueError(f"Unsupported upload type for {original_filename}. Supported types: {supported}.")
            payload.append(
                UploadCandidate(
                    original_filename=original_filename,
                    content=content,
                    content_type=file.content_type,
                    filename=filenames[index],
                    tags=parse_tags(tags[index]),
                )
            )

        result = upload_documents(payload)
        return DocumentUploadResponse(
            documents=result.documents,
            skipped=result.skipped,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Document upload failed")
        raise HTTPException(status_code=500, detail="Document upload failed") from exc


@router.post("/documents/index", response_model=IndexResponse)
def index_documents_endpoint(request: IndexRequest) -> IndexResponse:
    return index_endpoint(request)


@router.post("/documents/remove-vectors", response_model=DocumentActionResponse)
def remove_document_vectors_endpoint(
    request: DocumentIdsRequest,
) -> DocumentActionResponse:
    trace(f"Vector removal requested for {len(request.document_ids)} document(s)", logger)
    try:
        from app.services.vector_documents import remove_document_vectors

        result = remove_document_vectors(request.document_ids)
        return DocumentActionResponse(
            documents=result.documents,
            removed_vectors=result.removed_vectors,
        )
    except Exception as exc:
        logger.exception("Vector removal failed")
        raise HTTPException(status_code=500, detail="Vector removal failed") from exc


@router.post("/documents/remove", response_model=DocumentActionResponse)
def remove_documents_endpoint(request: DocumentIdsRequest) -> DocumentActionResponse:
    trace(f"Document removal requested for {len(request.document_ids)} document(s)", logger)
    try:
        from app.services.vector_documents import remove_documents_everywhere

        removed_documents, vector_result = remove_documents_everywhere(request.document_ids)
        return DocumentActionResponse(
            documents=vector_result.documents,
            removed_documents=removed_documents,
            removed_vectors=vector_result.removed_vectors,
        )
    except Exception as exc:
        logger.exception("Document removal failed")
        raise HTTPException(status_code=500, detail="Document removal failed") from exc


@router.get("/chat/sessions", response_model=ChatSessionsResponse)
def chat_sessions_endpoint() -> ChatSessionsResponse:
    trace("Chat sessions requested", logger)
    return ChatSessionsResponse(sessions=list_sessions())


@router.patch("/chat/sessions/{session_id}", response_model=ChatSessionsResponse)
def update_chat_session_endpoint(
    session_id: str,
    request: ChatSessionUpdateRequest,
) -> ChatSessionsResponse:
    trace("Chat session update requested", logger)
    try:
        update_session(session_id, title=request.title, archived=request.archived)
        return ChatSessionsResponse(sessions=list_sessions())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/chat/sessions/{session_id}", status_code=204)
def delete_chat_session_endpoint(session_id: str) -> None:
    trace("Chat session deletion requested", logger)
    try:
        delete_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/chat/sessions/{session_id}/interactions",
    response_model=ChatInteractionsResponse,
)
def chat_interactions_endpoint(session_id: str) -> ChatInteractionsResponse:
    trace("Chat interactions requested", logger)
    try:
        return ChatInteractionsResponse(interactions=list_interactions(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session id") from exc
