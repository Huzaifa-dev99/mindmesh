import re
import uuid
from dataclasses import dataclass

import httpx
from qdrant_client.http import models

from app.ai.embeddings.local import FastEmbedProvider
from app.ai.providers.groq import GroqChatProvider
from app.core.config import settings
from app.schemas.search import SearchResult
from app.services.vector_service import VectorService

try:
    from langchain_core.prompts import PromptTemplate
except ImportError:  # Keeps local Docker builds usable when LangChain is not installed.
    class PromptTemplate:  # type: ignore[no-redef]
        def __init__(self, template: str):
            self.template = template

        @classmethod
        def from_template(cls, template: str):
            return cls(template)

        def format(self, **kwargs):
            return self.template.format(**kwargs)

LOW_CONFIDENCE_THRESHOLD = 0.25


@dataclass
class AgentResult:
    route: str
    answer: str
    citations: list[SearchResult]
    metadata: dict


class NotesAgent:
    """RAG-only notes agent. It never answers without retrieved user note context."""

    def __init__(self) -> None:
        self.embeddings = FastEmbedProvider()
        self.vector_service = VectorService(settings.QDRANT_NOTES_COLLECTION)
        self.llm = GroqChatProvider()
        self.prompt = PromptTemplate.from_template(
            "You are the MindMesh Notes Agent. Answer only from the retrieved notes context. "
            "If the context is insufficient, say no relevant notes were found.\n\n"
            "Notes context:\n{context}\n\nQuestion: {question}\n\nAnswer with note source attribution."
        )

    async def answer(self, user_id: uuid.UUID, query: str, limit: int = 5) -> AgentResult:
        points = await self._retrieve(user_id, query, limit)
        if not points or points[0].score < LOW_CONFIDENCE_THRESHOLD:
            return AgentResult("notes", "I could not find relevant notes for that question.", [], {"confidence": 0})
        citations = [point_to_search_result(point, "note") for point in points]
        context = "\n\n".join(
            f"[{idx + 1}] {item.title or item.source_id}: {item.snippet}" for idx, item in enumerate(citations)
        )
        answer = await self.llm.complete([{"role": "user", "content": self.prompt.format(context=context, question=query)}])
        return AgentResult("notes", answer, citations, {"confidence": points[0].score})

    async def _retrieve(self, user_id: uuid.UUID, query: str, limit: int):
        vector = (await self.embeddings.embed([query]))[0]
        return await self.vector_service.search(
            vector,
            limit,
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchAny(any=["note", "journal"])),
                ]
            ),
        )


class DocumentsAgent:
    """RAG-only documents agent. It answers only from document chunks stored in Qdrant."""

    def __init__(self) -> None:
        self.embeddings = FastEmbedProvider()
        self.vector_service = VectorService(settings.QDRANT_DOCUMENTS_COLLECTION)
        self.llm = GroqChatProvider()
        self.prompt = PromptTemplate.from_template(
            "You are the MindMesh Documents Agent. Answer only from retrieved document chunks. "
            "If the context is insufficient, say no relevant documents were found. "
            "Cite file names and MinIO object paths when available.\n\n"
            "Document context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )

    async def answer(self, user_id: uuid.UUID, query: str, limit: int = 5) -> AgentResult:
        vector = (await self.embeddings.embed([query]))[0]
        points = await self.vector_service.search(
            vector,
            limit,
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                ]
            ),
        )
        if not points or points[0].score < LOW_CONFIDENCE_THRESHOLD:
            return AgentResult("documents", "I could not find relevant uploaded documents for that question.", [], {"confidence": 0})
        citations = [point_to_search_result(point, "document") for point in points]
        context = "\n\n".join(
            f"[{idx + 1}] {item.title}: {item.snippet}\nMinIO: {item.metadata.get('minio_object_path')}"
            for idx, item in enumerate(citations)
        )
        answer = await self.llm.complete([{"role": "user", "content": self.prompt.format(context=context, question=query)}])
        return AgentResult("documents", answer, citations, {"confidence": points[0].score})


class WebSearchAgent:
    def __init__(self, tavily_api_key: str | None = None) -> None:
        self.tavily_api_key = tavily_api_key or settings.TAVILY_API_KEY
        self.llm = GroqChatProvider()

    async def answer(self, query: str) -> AgentResult:
        if not self.tavily_api_key:
            return AgentResult(
                "web",
                "Web search is needed for this question, but Tavily is not configured. Add a Tavily API key in Settings -> Tools.",
                [],
                {"missing_tavily_api_key": True},
            )
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": self.tavily_api_key, "query": query, "search_depth": "advanced", "include_answer": True, "max_results": 5},
            )
            response.raise_for_status()
            payload = response.json()
        citations = [
            SearchResult(
                source_type="web",
                source_id=uuid.uuid5(uuid.NAMESPACE_URL, item.get("url", "")),
                score=float(item.get("score") or 0),
                title=item.get("title"),
                snippet=item.get("content") or item.get("url", ""),
                metadata={"url": item.get("url")},
            )
            for item in payload.get("results", [])
        ]
        answer = payload.get("answer") or await self._synthesize(query, citations)
        return AgentResult("web", answer, citations, {"result_count": len(citations)})

    async def _synthesize(self, query: str, citations: list[SearchResult]) -> str:
        context = "\n".join(f"[{idx + 1}] {item.title}: {item.snippet} ({item.metadata.get('url')})" for idx, item in enumerate(citations))
        return await self.llm.complete(
            [{"role": "user", "content": f"Answer using these web results with references.\n\n{context}\n\nQuestion: {query}"}]
        )


class SupervisorAgent:
    def __init__(self, tavily_api_key: str | None = None) -> None:
        self.notes_agent = NotesAgent()
        self.documents_agent = DocumentsAgent()
        self.web_agent = WebSearchAgent(tavily_api_key)
        self.llm = GroqChatProvider()

    async def answer(self, user_id: uuid.UUID, query: str, limit: int = 5) -> AgentResult:
        route = self.route(query)
        if route == "notes":
            return await self.notes_agent.answer(user_id, query, limit)
        if route == "documents":
            return await self.documents_agent.answer(user_id, query, limit)
        if route == "web":
            return await self.web_agent.answer(query)
        return AgentResult("direct", await self.direct_answer(query), [], {})

    def route(self, query: str) -> str:
        normalized = query.lower()
        if re.search(r"\b(my notes|saved notes|notes?|ideas i wrote|personal knowledge)\b", normalized):
            return "notes"
        if re.search(r"\b(uploaded|file|files|pdf|document|documents|report|attachment|attachments)\b", normalized):
            return "documents"
        if re.search(r"\b(today|latest|current|news|online|web|internet|recent|now|2026|price|weather)\b", normalized):
            return "web"
        if re.search(r"\b(hi|hello|hey|thanks|help)\b", normalized):
            return "direct"
        return "notes"

    async def direct_answer(self, query: str) -> str:
        if re.search(r"\b(hi|hello|hey)\b", query.lower()):
            return "Hi, I am MindMesh. Ask me about your notes, uploaded documents, or current web information if Tavily is configured."
        return await self.llm.complete(
            [{"role": "user", "content": f"You are the MindMesh Supervisor Agent. Briefly help with app usage or ask for clarification.\n\nUser: {query}"}]
        )


def point_to_search_result(point, default_source_type: str) -> SearchResult:
    payload = point.payload or {}
    source_id = payload.get("source_id") or payload.get("document_id") or str(uuid.uuid4())
    return SearchResult(
        source_type=payload.get("source_type") or default_source_type,
        source_id=uuid.UUID(source_id),
        score=point.score,
        title=payload.get("title") or payload.get("file_name"),
        snippet=payload.get("text", ""),
        metadata={key: value for key, value in payload.items() if key != "text"},
    )
