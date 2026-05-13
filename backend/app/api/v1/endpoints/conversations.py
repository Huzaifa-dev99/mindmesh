import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import MessageResponse
from app.schemas.conversation import ConversationDetail, ConversationSummary, ConversationUpdate

router = APIRouter()


def _summary(conversation: Conversation) -> ConversationSummary:
    messages = sorted(conversation.messages, key=lambda item: item.created_at)
    last_message = messages[-1] if messages else None
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages),
        last_message_at=last_message.created_at if last_message else None,
    )


def _detail(conversation: Conversation) -> ConversationDetail:
    summary = _summary(conversation)
    messages = [
        MessageResponse.model_validate(message)
        for message in sorted(conversation.messages, key=lambda item: item.created_at)
    ]
    return ConversationDetail(**summary.model_dump(), messages=messages)


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = await ConversationRepository(db).list_for_user(current_user.id)
    return [_summary(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await ConversationRepository(db).get_by_id(current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _detail(conversation)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = ConversationRepository(db)
    conversation = await repository.get_by_id(current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _summary(await repository.update_title(conversation, payload.title))


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = ConversationRepository(db)
    conversation = await repository.get_by_id(current_user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await repository.soft_delete(conversation)
    return Response(status_code=204)
