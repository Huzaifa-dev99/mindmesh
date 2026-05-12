import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.templates import SYSTEM_PROMPT
from app.ai.providers.groq import GroqChatProvider
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService


class ChatService:
    def __init__(self, session: AsyncSession):
        self.conversations = ConversationRepository(session)
        self.search_service = SearchService()
        self.ai = GroqChatProvider()

    async def chat(self, user_id: uuid.UUID, request: ChatRequest) -> ChatResponse:
        conversation = await self.conversations.get_or_create(user_id, request.conversation_id)
        await self.conversations.add_message(conversation.id, "user", request.message)

        citations = []
        context = ""
        if request.use_rag:
            search = await self.search_service.search(
                user_id, SearchRequest(query=request.message, limit=request.limit)
            )
            citations = search.results
            context = "\n\n".join(
                f"[{idx + 1}] {item.source_type} {item.title or item.source_id}: {item.snippet}"
                for idx, item in enumerate(citations)
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context or 'No retrieved context.'}\n\nQuestion:\n{request.message}"},
        ]
        answer = await self.ai.complete(messages)
        await self.conversations.add_message(
            conversation.id,
            "assistant",
            answer,
            {"citation_count": len(citations)},
        )
        return ChatResponse(conversation_id=conversation.id, answer=answer, citations=citations)
