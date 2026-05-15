import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.note import NoteCreate, NoteResponse, NoteScopeUpdate, NoteUpdate
from app.schemas.document import DocumentScopeUpdate, DocumentUpload
from app.schemas.tag import TagResponse
from app.services.content_service import NoteService
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/notes", response_model=list[NoteResponse])
async def list_notes(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NoteService(db).list_notes(current_user.id)


@router.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await NoteService(db).create_note(current_user.id, payload)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await NoteService(db).update_note(note_id, current_user.id, payload)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NoteService(db).delete_note(note_id, current_user.id)
    return Response(status_code=204)


@router.patch("/notes/{note_id}/scope", response_model=NoteResponse)
async def update_note_scope(
    note_id: uuid.UUID,
    payload: NoteScopeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await NoteService(db).update_scope(note_id, current_user.id, payload.scope, payload.chat_id)


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NoteService(db).list_tags(current_user.id)


@router.get("/documents")
async def list_documents(
    scope: str | None = None,
    chat_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
):
    return await DocumentService().list_documents(current_user.id, scope=scope, chat_id=chat_id)


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    payload = await parse_document_upload(request)
    return await DocumentService().upload_and_ingest(
        current_user.id,
        file_name=payload.file_name,
        content=payload.content,
        file_bytes=payload.file_bytes,
        file_type=payload.file_type,
        scope=payload.scope,
        chat_id=payload.chat_id,
        selected_model_id=payload.selected_model_id,
        selected_model_supports_vision=payload.selected_model_supports_vision,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    await DocumentService().delete_document(current_user.id, document_id)
    return Response(status_code=204)


@router.patch("/documents/{document_id}/scope")
async def update_document_scope(
    document_id: uuid.UUID,
    payload: DocumentScopeUpdate,
    current_user: User = Depends(get_current_user),
):
    return await DocumentService().update_scope(current_user.id, document_id, payload.scope, payload.chat_id)


class ParsedDocumentUpload(DocumentUpload):
    file_bytes: bytes | None = None


async def parse_document_upload(request: Request) -> ParsedDocumentUpload:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="Document file is required")
        file_bytes = await upload.read()
        chat_id_raw = form.get("chat_id")
        return ParsedDocumentUpload(
            file_name=getattr(upload, "filename", None) or "document",
            content=None,
            file_bytes=file_bytes,
            file_type=getattr(upload, "content_type", None) or "application/octet-stream",
            scope=str(form.get("scope") or "global"),
            chat_id=uuid.UUID(str(chat_id_raw)) if chat_id_raw else None,
            selected_model_id=str(form.get("selected_model_id")) if form.get("selected_model_id") else None,
            selected_model_supports_vision=str(form.get("selected_model_supports_vision") or "").lower() == "true",
        )
    payload = await request.json()
    return ParsedDocumentUpload.model_validate(payload)
