import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_settings_service import AISettingsService
from app.services.agents import SupervisorAgent


class ChatService:
    def __init__(self, session: AsyncSession):
        self.conversations = ConversationRepository(session)

    async def chat(self, user_id: uuid.UUID, request: ChatRequest) -> ChatResponse:
        conversation = await self.conversations.get_or_create(user_id, request.conversation_id)
        existing_messages = conversation.__dict__.get("messages", [])
        message_count = len(existing_messages)
        await self.conversations.add_message(conversation.id, "user", request.message)
        if message_count == 0 and conversation.title == "New conversation":
            title = request.message.strip().replace("\n", " ")
            await self.conversations.update_title(conversation, title[:80] or "New conversation")

        ai_settings = AISettingsService()
        provider, selected_model = request.provider, request.model_id
        if not provider or not selected_model:
            provider, selected_model = ai_settings.get_chat_model(user_id, conversation.id)
        api_key = ai_settings.get_api_key(user_id, provider)
        result = await SupervisorAgent(
            request.tavily_api_key,
            provider=provider,
            model=selected_model,
            api_key=api_key,
        ).answer(user_id, request.message, request.limit, conversation.id)
        await self.conversations.add_message(
            conversation.id,
            "assistant",
            result.answer,
            {
                "citation_count": len(result.citations),
                "route": result.route,
                "provider": provider,
                "model": selected_model,
                **result.metadata,
            },
        )
        return ChatResponse(
            conversation_id=conversation.id,
            answer=result.answer,
            citations=result.citations,
            metadata={"route": result.route, "provider": provider, "model": selected_model, **result.metadata},
        )
