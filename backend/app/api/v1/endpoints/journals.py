import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalResponse, JournalSummary, JournalUpdate
from app.services.content_service import JournalService

router = APIRouter()


@router.get("", response_model=list[JournalResponse])
async def list_journals(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await JournalService(db).list_journals(current_user.id)


@router.post("", response_model=JournalResponse, status_code=201)
async def create_journal(
    payload: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await JournalService(db).create_journal(current_user.id, payload)


@router.patch("/{journal_id}", response_model=JournalResponse)
async def update_journal(
    journal_id: uuid.UUID,
    payload: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await JournalService(db).update_journal(journal_id, current_user.id, payload)


@router.delete("/{journal_id}", status_code=204)
async def delete_journal(
    journal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await JournalService(db).delete_journal(journal_id, current_user.id)
    return Response(status_code=204)


@router.post("/{journal_id}/summary", response_model=JournalSummary)
async def summarize_journal(
    journal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await JournalService(db).summarize(journal_id, current_user.id)
