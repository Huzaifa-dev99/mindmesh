import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.schemas.document import DocumentUpload
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


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NoteService(db).list_tags(current_user.id)


@router.get("/documents")
async def list_documents(current_user: User = Depends(get_current_user)):
    return await DocumentService().list_documents(current_user.id)


@router.post("/documents", status_code=201)
async def upload_document(
    payload: DocumentUpload,
    current_user: User = Depends(get_current_user),
):
    return await DocumentService().upload_and_ingest(
        current_user.id,
        file_name=payload.file_name,
        content=payload.content,
        file_type=payload.file_type,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    await DocumentService().delete_document(current_user.id, document_id)
    return Response(status_code=204)
