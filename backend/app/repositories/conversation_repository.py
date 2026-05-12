import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: uuid.UUID, conversation_id: uuid.UUID | None) -> Conversation:
        conversation = None
        if conversation_id:
            result = await self.session.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                    Conversation.deleted_at.is_(None),
                )
            )
            conversation = result.scalar_one_or_none()
        if conversation is None:
            conversation = Conversation(user_id=user_id, title="New conversation")
            self.session.add(conversation)
            await self.session.flush()
        return conversation

    async def add_message(
        self, conversation_id: uuid.UUID, role: str, content: str, metadata: dict | None = None
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 30) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
