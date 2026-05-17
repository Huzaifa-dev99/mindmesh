from __future__ import annotations

import re
import uuid
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from app.ai.providers.groq import GroqChatProvider
from app.core.config import settings
from app.schemas.search import SearchResult

if TYPE_CHECKING:
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
MAX_HISTORY_SUMMARY_CHARS = 1800
MAX_RETRIEVAL_QUERY_CHARS = 3000
MAX_STANDALONE_QUERY_CHARS = 700

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    route: str
    answer: str
    citations: list[SearchResult]
    metadata: dict


@dataclass
class RetrievedContext:
    source_type: str
    context: str
    citations: list[SearchResult]
    confidence: float


@dataclass
class QueryRewriteResult:
    original_query: str
    query: str
    rewritten: bool
    strategy: str


def create_embedding_provider():
    from app.ai.embeddings.local import FastEmbedProvider

    return FastEmbedProvider()


def create_vector_service(collection_name: str):
    from app.services.vector_service import VectorService

    return VectorService(collection_name)


def get_qdrant_models():
    from qdrant_client.http import models

    return models


def build_chat_history_summary(messages: list[Any], max_messages: int = 12, max_chars: int = MAX_HISTORY_SUMMARY_CHARS) -> str:
    if not messages:
        return "No previous chat history."

    ordered_messages = sorted(messages, key=lambda item: str(getattr(item, "created_at", "") or ""))
    selected_messages = ordered_messages[-max_messages:]
    lines = []
    for message in selected_messages:
        role = getattr(message, "role", "message")
        content = " ".join(str(getattr(message, "content", "")).split())
        if not content:
            continue
        lines.append(f"{role}: {content}")

    summary = "\n".join(lines).strip()
    if not summary:
        return "No previous chat history."
    if len(summary) > max_chars:
        return summary[-max_chars:].lstrip()
    return summary


def build_retrieval_query(query: str, chat_history_summary: str | None = None) -> str:
    history = (chat_history_summary or "No previous chat history.").strip()
    retrieval_query = f"Current user question:\n{query.strip()}\n\nRelevant chat history summary:\n{history}"
    if len(retrieval_query) > MAX_RETRIEVAL_QUERY_CHARS:
        return retrieval_query[:MAX_RETRIEVAL_QUERY_CHARS]
    return retrieval_query


def has_prior_chat_history(chat_history_summary: str | None) -> bool:
    return bool(chat_history_summary and chat_history_summary.strip() != "No previous chat history.")


def clean_rewritten_query(value: str, original_query: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^```(?:text)?|```$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip("\"'` ")
    cleaned = re.sub(
        r"^(?:standalone(?: search)? query|rewritten(?: search)? query|query)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = " ".join(cleaned.split())
    if not cleaned or "groq is not configured" in cleaned.lower():
        return original_query.strip()
    if len(cleaned) > MAX_STANDALONE_QUERY_CHARS:
        cleaned = cleaned[:MAX_STANDALONE_QUERY_CHARS].rsplit(" ", 1)[0].strip()
    return cleaned or original_query.strip()


def last_user_turn_from_history(chat_history_summary: str | None) -> str:
    if not has_prior_chat_history(chat_history_summary):
        return ""
    for line in reversed((chat_history_summary or "").splitlines()):
        if line.lower().startswith("user:"):
            return line.split(":", 1)[1].strip()
    return ""


def looks_contextual_follow_up(query: str) -> bool:
    normalized = query.lower().strip()
    if len(normalized.split()) <= 8:
        return True
    return bool(
        re.search(
            r"\b(it|this|that|these|those|they|them|their|he|she|his|her|there|same|previous|above|earlier|also)\b",
            normalized,
        )
        or normalized.startswith(("what about", "how about", "and ", "also ", "then ", "why ", "when ", "where "))
    )


def build_fallback_standalone_query(query: str, chat_history_summary: str | None) -> str:
    original_query = query.strip()
    if not has_prior_chat_history(chat_history_summary) or not looks_contextual_follow_up(original_query):
        return original_query
    last_user_turn = last_user_turn_from_history(chat_history_summary)
    if not last_user_turn:
        return original_query
    fallback = f"{last_user_turn} Follow-up question: {original_query}"
    if len(fallback) > MAX_STANDALONE_QUERY_CHARS:
        return fallback[-MAX_STANDALONE_QUERY_CHARS:].lstrip()
    return fallback


class QueryRewriter:
    def __init__(self, llm: GroqChatProvider | None = None) -> None:
        self.llm = llm or GroqChatProvider()
        self.prompt = PromptTemplate.from_template(
            "Rewrite the current user message as one standalone semantic search query.\n"
            "Use the chat history to resolve pronouns, ellipses, and references such as "
            "'it', 'that', 'they', 'the previous one', or 'what about'. Preserve names, dates, "
            "constraints, and the user's intent. Do not answer the question. If the current "
            "message is already standalone, return it unchanged. Return only the standalone query.\n\n"
            "Chat history:\n{chat_history_summary}\n\n"
            "Current user message:\n{query}\n\n"
            "Standalone query:"
        )

    async def rewrite(self, query: str, chat_history_summary: str | None = None) -> QueryRewriteResult:
        original_query = query.strip()
        if not has_prior_chat_history(chat_history_summary):
            return QueryRewriteResult(original_query, original_query, False, "none")

        fallback_query = build_fallback_standalone_query(original_query, chat_history_summary)
        try:
            rewritten_query = await self.llm.complete(
                [
                    {
                        "role": "user",
                        "content": self.prompt.format(
                            chat_history_summary=chat_history_summary,
                            query=original_query,
                        ),
                    }
                ],
                temperature=0,
            )
            cleaned_query = clean_rewritten_query(rewritten_query, original_query)
            if cleaned_query == original_query and fallback_query != original_query:
                cleaned_query = fallback_query
                strategy = "fallback"
            else:
                strategy = "llm" if cleaned_query != original_query else "unchanged"
            return QueryRewriteResult(original_query, cleaned_query, cleaned_query != original_query, strategy)
        except Exception:
            logger.warning("query_rewrite_failed falling_back_to_heuristic", exc_info=True)
            return QueryRewriteResult(original_query, fallback_query, fallback_query != original_query, "fallback")


class NotesAgent:
    """RAG-only notes agent. It never answers without retrieved user note context."""

    def __init__(self, embeddings=None, vector_service: VectorService | None = None, llm: GroqChatProvider | None = None) -> None:
        self.embeddings = embeddings or create_embedding_provider()
        self.vector_service = vector_service or create_vector_service(settings.QDRANT_NOTES_COLLECTION)
        self.llm = llm or GroqChatProvider()
        self.prompt = PromptTemplate.from_template(
            "You are the MindMesh Notes Agent. Answer only from the retrieved notes context. "
            "If the context is insufficient, say no relevant notes were found.\n\n"
            "Chat history summary:\n{chat_history_summary}\n\n"
            "Notes context:\n{context}\n\nQuestion: {question}\n\nAnswer with note source attribution."
        )

    async def answer(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> AgentResult:
        retrieved = await self.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        if not retrieved.citations:
            return AgentResult("notes", "I could not find relevant notes for that question.", [], {"confidence": 0})
        answer = await self.llm.complete(
            [
                {
                    "role": "user",
                    "content": self.prompt.format(
                        chat_history_summary=chat_history_summary or "No previous chat history.",
                        context=retrieved.context,
                        question=query,
                    ),
                }
            ]
        )
        return AgentResult("notes", answer, retrieved.citations, {"confidence": retrieved.confidence})

    async def retrieve_context(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> RetrievedContext:
        retrieval_query = build_retrieval_query(query, chat_history_summary)
        points = await self._retrieve(user_id, retrieval_query, limit, conversation_id)
        citations = [point_to_search_result(point, "note") for point in points]
        context = "\n\n".join(
            f"[N{idx + 1}] {item.title or item.source_id}\n{item.snippet}" for idx, item in enumerate(citations)
        )
        confidence = points[0].score if points else 0
        return RetrievedContext("notes", context, citations, confidence)

    async def _retrieve(self, user_id: uuid.UUID, query: str, limit: int, conversation_id: uuid.UUID | None):
        models = get_qdrant_models()
        vector = (await self.embeddings.embed([query]))[0]
        journal_points = await self.vector_service.search(
            vector,
            limit,
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="journal")),
                ]
            ),
        )
        global_note_points = await self.vector_service.search(
            vector,
            limit,
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="note")),
                    models.FieldCondition(key="scope", match=models.MatchValue(value="global")),
                ]
            ),
        )
        chat_note_points = []
        if conversation_id:
            chat_note_points = await self.vector_service.search(
                vector,
                limit,
                models.Filter(
                    must=[
                        models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                        models.FieldCondition(key="source_type", match=models.MatchValue(value="note")),
                        models.FieldCondition(key="scope", match=models.MatchValue(value="chat")),
                        models.FieldCondition(key="chat_id", match=models.MatchValue(value=str(conversation_id))),
                    ]
                ),
            )
        return sorted([*journal_points, *global_note_points, *chat_note_points], key=lambda point: point.score, reverse=True)[:limit]


class DocumentsAgent:
    """RAG-only documents agent. It answers only from document chunks stored in Qdrant."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        embeddings=None,
        vector_service: VectorService | None = None,
        llm: GroqChatProvider | None = None,
    ) -> None:
        self.embeddings = embeddings or create_embedding_provider()
        self.vector_service = vector_service or create_vector_service(settings.QDRANT_DOCUMENTS_COLLECTION)
        self.llm = llm or GroqChatProvider(model=model or "llama-3.1-8b-instant", api_key=api_key)
        self.prompt = PromptTemplate.from_template(
            "You are the MindMesh Documents Agent. Answer only from retrieved document chunks. "
            "If the context is insufficient, say no relevant documents were found. "
            "Cite file names and MinIO object paths when available.\n\n"
            "Chat history summary:\n{chat_history_summary}\n\n"
            "Document context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )

    async def answer(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> AgentResult:
        retrieved = await self.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        if not retrieved.citations:
            return AgentResult("documents", "I could not find relevant uploaded documents for that question.", [], {"confidence": 0})
        answer = await self.llm.complete(
            [
                {
                    "role": "user",
                    "content": self.prompt.format(
                        chat_history_summary=chat_history_summary or "No previous chat history.",
                        context=retrieved.context,
                        question=query,
                    ),
                }
            ]
        )
        return AgentResult("documents", answer, retrieved.citations, {"confidence": retrieved.confidence})

    async def retrieve_context(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> RetrievedContext:
        retrieval_query = build_retrieval_query(query, chat_history_summary)
        points = await self.retrieve(user_id, retrieval_query, limit, conversation_id)
        citations = [point_to_search_result(point, "document") for point in points]
        context = "\n\n".join(
            f"[D{idx + 1}] {item.title or item.source_id}\n{item.snippet}\nMinIO: {item.metadata.get('minio_object_path')}"
            for idx, item in enumerate(citations)
        )
        confidence = points[0].score if points else 0
        return RetrievedContext("documents", context, citations, confidence)

    async def retrieve(self, user_id: uuid.UUID, query: str, limit: int = 5, conversation_id: uuid.UUID | None = None):
        models = get_qdrant_models()
        vector = (await self.embeddings.embed([query]))[0]
        global_points = await self.vector_service.search(
            vector,
            limit,
            models.Filter(
                must=[
                    models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                    models.FieldCondition(key="scope", match=models.MatchValue(value="global")),
                ]
            ),
        )
        chat_points = []
        if conversation_id:
            chat_points = await self.vector_service.search(
                vector,
                limit,
                models.Filter(
                    must=[
                        models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id))),
                        models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                        models.FieldCondition(key="scope", match=models.MatchValue(value="chat")),
                        models.FieldCondition(key="chat_id", match=models.MatchValue(value=str(conversation_id))),
                    ]
                ),
            )
        points = sorted([*global_points, *chat_points], key=lambda point: point.score, reverse=True)[:limit]
        return points


class WorkspaceAgent:
    """RAG agent that considers both notes/journals and uploaded documents."""

    def __init__(self, notes_agent: NotesAgent, documents_agent: DocumentsAgent, llm: GroqChatProvider) -> None:
        self.notes_agent = notes_agent
        self.documents_agent = documents_agent
        self.llm = llm
        self.prompt = PromptTemplate.from_template(
            "You are MindMesh. Answer from the retrieved workspace context and chat history summary. "
            "Use both notes and uploaded documents when relevant. If context is insufficient, say what is missing.\n\n"
            "Chat history summary:\n{chat_history_summary}\n\n"
            "Notes Agent context:\n{notes_context}\n\n"
            "Documents Agent context:\n{documents_context}\n\n"
            "Question: {question}\n\nAnswer with source attribution:"
        )

    async def answer(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> AgentResult:
        notes = await self.notes_agent.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        documents = await self.documents_agent.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        citations = [*notes.citations, *documents.citations]
        confidence = max(notes.confidence, documents.confidence)
        if not citations:
            return AgentResult("workspace", "I could not find relevant notes or uploaded documents for that question.", [], {"confidence": 0})
        answer = await self.llm.complete(
            [
                {
                    "role": "user",
                    "content": self.prompt.format(
                        chat_history_summary=chat_history_summary or "No previous chat history.",
                        notes_context=notes.context or "No relevant notes were retrieved.",
                        documents_context=documents.context or "No relevant documents were retrieved.",
                        question=query,
                    ),
                }
            ]
        )
        return AgentResult(
            "workspace",
            answer,
            citations,
            {
                "confidence": confidence,
                "notes_context_count": len(notes.citations),
                "documents_context_count": len(documents.citations),
                "notes_confidence": notes.confidence,
                "documents_confidence": documents.confidence,
                "low_confidence": bool(citations and confidence < LOW_CONFIDENCE_THRESHOLD),
                "chat_history_included": has_prior_chat_history(chat_history_summary),
            },
        )


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
    def __init__(
        self,
        tavily_api_key: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.notes_agent = NotesAgent()
        self.provider = provider or "Groq"
        self.model = model
        groq_model = model if self.provider == "Groq" else None
        groq_key = api_key if self.provider == "Groq" else None
        self.documents_agent = DocumentsAgent(model=groq_model, api_key=groq_key)
        self.web_agent = WebSearchAgent(tavily_api_key)
        self.llm = GroqChatProvider(model=groq_model or "llama-3.1-8b-instant", api_key=groq_key)
        self.query_rewriter = QueryRewriter(self.llm)
        self.workspace_agent = WorkspaceAgent(self.notes_agent, self.documents_agent, self.llm)
        self.prompt = PromptTemplate.from_template(
            "You are the MindMesh Supervisor Agent. Use the chat history summary, Notes Agent context, "
            "and Documents Agent context to answer the current question. The agents already retrieved "
            "chunks using both the current question and chat history, so treat their context as the "
            "available workspace knowledge.\n\n"
            "Rules:\n"
            "- Prefer retrieved notes and documents over general knowledge.\n"
            "- Use both sources when both are relevant.\n"
            "- If the retrieved context is insufficient, say exactly what is missing.\n"
            "- Cite source labels such as [N1] or [D1] when using retrieved context.\n\n"
            "Chat history summary:\n{chat_history_summary}\n\n"
            "Original user question:\n{original_question}\n\n"
            "Standalone question used for retrieval:\n{question}\n\n"
            "Notes Agent context:\n{notes_context}\n\n"
            "Documents Agent context:\n{documents_context}\n\n"
            "Answer:"
        )

    async def answer(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
        conversation_id: uuid.UUID | None = None,
        chat_history_summary: str | None = None,
    ) -> AgentResult:
        rewrite_result = await self.rewrite_query(query, chat_history_summary)
        route = self.route(rewrite_result.query)
        if route == "web":
            result = await self.web_agent.answer(rewrite_result.query)
            return self.with_query_rewrite_metadata(result, rewrite_result)
        if route == "workspace":
            result = await self.answer_from_workspace_context(
                user_id,
                rewrite_result.query,
                limit,
                conversation_id,
                chat_history_summary,
                original_query=rewrite_result.original_query,
                rewrite_result=rewrite_result,
            )
            return self.with_query_rewrite_metadata(result, rewrite_result)
        return self.with_query_rewrite_metadata(
            AgentResult("direct", await self.direct_answer(rewrite_result.original_query), [], {}),
            rewrite_result,
        )

    async def rewrite_query(self, query: str, chat_history_summary: str | None) -> QueryRewriteResult:
        rewriter = getattr(self, "query_rewriter", None)
        if rewriter is None:
            rewriter = QueryRewriter(getattr(self, "llm", None))
            self.query_rewriter = rewriter
        return await rewriter.rewrite(query, chat_history_summary)

    def with_query_rewrite_metadata(self, result: AgentResult, rewrite_result: QueryRewriteResult) -> AgentResult:
        result.metadata = {
            **result.metadata,
            "original_query": rewrite_result.original_query,
            "rewritten_query": rewrite_result.query,
            "query_rewritten": rewrite_result.rewritten,
            "query_rewrite_strategy": rewrite_result.strategy,
        }
        return result

    def route(self, query: str) -> str:
        normalized = query.lower().strip()
        if re.search(r"\b(today|latest|news|online|web|internet|recent|now|2026|price|weather|current events)\b", normalized):
            return "web"
        if re.fullmatch(r"(hi|hello|hey|thanks|thank you|help)[.!?]*", normalized):
            return "direct"
        return "workspace"

    async def answer_from_workspace_context(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int,
        conversation_id: uuid.UUID | None,
        chat_history_summary: str | None,
        original_query: str | None = None,
        rewrite_result: QueryRewriteResult | None = None,
    ) -> AgentResult:
        notes = await self.notes_agent.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        documents = await self.documents_agent.retrieve_context(user_id, query, limit, conversation_id, chat_history_summary)
        citations = [*notes.citations, *documents.citations]
        confidence = max(notes.confidence, documents.confidence)
        if not citations:
            return AgentResult(
                "workspace",
                "I could not find relevant notes or uploaded documents for that question.",
                [],
                {
                    "confidence": 0,
                    "notes_context_count": 0,
                    "documents_context_count": 0,
                    "chat_history_included": has_prior_chat_history(chat_history_summary),
                },
            )
        answer = await self.llm.complete(
            [
                {
                    "role": "user",
                    "content": self.prompt.format(
                        chat_history_summary=chat_history_summary or "No previous chat history.",
                        original_question=original_query or query,
                        question=query,
                        notes_context=notes.context or "No relevant notes were retrieved.",
                        documents_context=documents.context or "No relevant documents were retrieved.",
                    ),
                }
            ]
        )
        return AgentResult(
            "workspace",
            answer,
            citations,
            {
                "confidence": confidence,
                "notes_context_count": len(notes.citations),
                "documents_context_count": len(documents.citations),
                "notes_confidence": notes.confidence,
                "documents_confidence": documents.confidence,
                "low_confidence": bool(citations and confidence < LOW_CONFIDENCE_THRESHOLD),
                "chat_history_included": has_prior_chat_history(chat_history_summary),
            },
        )

    async def direct_answer(self, query: str) -> str:
        if self.provider != "Groq":
            return (
                f"{self.provider} is selected with model {self.model or 'default'}, but chat generation is currently wired "
                "through Groq-compatible responses in this local build. Documents and model metadata are still managed provider-agnostically."
            )
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
