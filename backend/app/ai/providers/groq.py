import httpx

from app.ai.providers.base import ChatProvider
from app.core.config import settings


class GroqChatProvider(ChatProvider):
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def complete(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not settings.GROQ_API_KEY:
            return (
                "Groq is not configured. Add GROQ_API_KEY to enable AI responses. "
                "Your content is still stored and searchable locally."
            )
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={"model": self.model, "messages": messages, "temperature": temperature},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
