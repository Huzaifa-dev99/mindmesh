from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import RETRIEVER_SCORE_THRESHOLD, RETRIEVER_TOP_K
from app.core.logging import get_logger, log_timing, trace
from app.services.prompts import (
    CONTEXTUALIZE_PROMPT_NAME,
    DIRECT_PROMPT_NAME,
    SYSTEM_PROMPT_NAME,
    WEB_SEARCH_PROMPT_NAME,
    render_prompt,
)
from app.services.retrieval import RetrievedContext, format_context, retrieve_context
from app.services.router import RouteDecision, route_query
from app.services.websearch import format_web_context, search_web

logger = get_logger(__name__)


@dataclass
class AiResponse:
    answer: str
    query: str
    contextualized_query: str
    contexts: list[RetrievedContext]
    route: str = "retrieval"
    route_reasoning: str = ""
    session_id: str | None = None
    interaction_id: str | None = None

    @property
    def sources(self) -> list[dict]:
        sources = []
        for context in self.contexts:
            metadata = dict(context.metadata or {})
            sources.append(
                {
                    "source": context.source_label,
                    "score": context.score,
                    "vector_id": metadata.get("_id"),
                    "collection_name": metadata.get("_collection_name"),
                    "metadata": {
                        key: value
                        for key, value in context.reference_metadata.items()
                        if value not in (None, "")
                    },
                }
            )

        return sources


def _format_chat_history(history: list[dict[str, Any]] | None, max_turns: int = 8) -> str:
    if not history:
        return "No prior chat history."

    turns = history[-max_turns:]
    formatted = []
    for index, interaction in enumerate(turns, start=1):
        query = str(interaction.get("query") or "").strip()
        answer = str(interaction.get("answer") or "").strip()
        if not query and not answer:
            continue

        formatted.append(f"Turn {index}")
        if query:
            formatted.append(f"User: {query}")
        if answer:
            formatted.append(f"Assistant: {answer}")

    return "\n".join(formatted) if formatted else "No prior chat history."


def build_prompt(
    query: str,
    contexts: list[RetrievedContext],
    contextualized_query: str | None = None,
) -> list:
    context_text = format_context(contexts)
    prompt = render_prompt(
        SYSTEM_PROMPT_NAME,
        query=query.strip(),
        contextualized_query=(contextualized_query or query).strip(),
        context=context_text,
    )
    return [
        SystemMessage(content=prompt),
        HumanMessage(content=query.strip()),
    ]


def build_web_prompt(
    query: str,
    contexts: list[RetrievedContext],
    tavily_answer: str | None = None,
) -> list:
    prompt = render_prompt(
        WEB_SEARCH_PROMPT_NAME,
        query=query.strip(),
        context=format_web_context(contexts, tavily_answer=tavily_answer),
    )
    return [
        SystemMessage(content=prompt),
        HumanMessage(content=query.strip()),
    ]


def contextualize_query(query: str, history: list[dict[str, Any]] | None = None, llm=None) -> str:
    """Rewrite a follow-up query into a standalone retrieval query."""
    trace("Query contextualization started", logger)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if not history:
        logger.info("query contextualization skipped without history")
        trace("Query contextualization skipped without history", logger)
        return query.strip()

    if llm is None:
        from app.core.clients import get_llm

        llm = get_llm()

    prompt = render_prompt(
        CONTEXTUALIZE_PROMPT_NAME,
        query=query.strip(),
        history=_format_chat_history(history),
    )
    with log_timing(logger, "llm_contextualize_query", history_count=len(history)):
        response = llm.invoke([HumanMessage(content=prompt)])
    contextualized_query = str(response.content or "").strip()
    logger.info(
        "query contextualization completed",
        extra={"event": {"history_count": len(history), "rewritten": contextualized_query != query.strip()}},
    )
    trace("Query contextualization completed", logger)

    return contextualized_query or query.strip()


def _load_history(
    session_id: str | None,
    history: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if history is not None:
        return history
    if not session_id:
        return []

    from app.services.chat_history import list_interactions

    return list_interactions(session_id)


def answer_question(
    query: str,
    history: list[dict[str, Any]] | None = None,
    top_k: int = RETRIEVER_TOP_K,
    score_threshold: float = RETRIEVER_SCORE_THRESHOLD,
    session_id: str | None = None,
    document_ids: list[str] | None = None,
    tags: list[str] | None = None,
    retrieval_enabled: bool = True,
    web_search_enabled: bool = True,
    route_mode: str | None = None,
    model: str | None = None,
) -> AiResponse:
    from app.core.clients import get_llm_for_model
    from app.services.chat_history import record_interaction

    trace("Answer generation started", logger)
    logger.info(
        "answer generation started",
        extra={
            "event": {
                "top_k": top_k,
                "score_threshold": score_threshold,
                "has_session": bool(session_id),
                "document_filter_count": len(document_ids or []),
                "tag_filter_count": len(tags or []),
                "retrieval_enabled": retrieval_enabled,
                "web_search_enabled": web_search_enabled,
                "route_mode": route_mode,
                "model": model,
            }
        },
    )
    llm = get_llm_for_model(model)
    chat_history = _load_history(session_id=session_id, history=history)
    contextualized_query = contextualize_query(query, chat_history, llm=llm)

    route = _resolve_route(
        contextualized_query,
        llm=llm,
        document_ids=document_ids,
        tags=tags,
        retrieval_enabled=retrieval_enabled,
        web_search_enabled=web_search_enabled,
        route_mode=route_mode,
    )
    logger.info(
        "query route selected",
        extra={"event": {"route": route.route, "reasoning": route.reasoning}},
    )
    trace(f"Query routed to {route.route}", logger)
    if route.route == "web_search":
        with log_timing(logger, "web_answer_generation"):
            web_result = search_web(contextualized_query)
            response = llm.invoke(
                build_web_prompt(
                    query=query,
                    contexts=web_result.contexts,
                    tavily_answer=web_result.answer,
                )
            )
        answer = str(response.content or "").strip()
        contexts = web_result.contexts
        interaction = record_interaction(
            query=query,
            contextualized_query=contextualized_query,
            answer=answer,
            contexts=contexts,
            top_k=top_k,
            score_threshold=score_threshold,
            route=route.route,
            route_reasoning=route.reasoning,
            session_id=session_id,
        )
        trace("Answer generation completed", logger)
        return AiResponse(
            answer=answer,
            query=query,
            contextualized_query=contextualized_query,
            contexts=contexts,
            route=route.route,
            route_reasoning=route.reasoning,
            session_id=interaction["session_id"],
            interaction_id=interaction["interaction_id"],
        )
    if route.route == "retrieval":
        with log_timing(logger, "retrieval_answer_generation", top_k=top_k):
            contexts = retrieve_context(
                contextualized_query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_ids=document_ids,
                tags=tags,
            )
            response = llm.invoke(
                build_prompt(
                    query=query,
                    contexts=contexts,
                    contextualized_query=contextualized_query,
                )
            )
        answer = response.content
        interaction = record_interaction(
            query=query,
            contextualized_query=contextualized_query,
            answer=answer,
            contexts=contexts,
            top_k=top_k,
            score_threshold=score_threshold,
            route=route.route,
            route_reasoning=route.reasoning,
            session_id=session_id,
        )

        trace("Answer generation completed", logger)
        return AiResponse(
            answer=answer,
            query=query,
            contextualized_query=contextualized_query,
            contexts=contexts,
            route=route.route,
            route_reasoning=route.reasoning,
            session_id=interaction["session_id"],
            interaction_id=interaction["interaction_id"],
        )

    with log_timing(logger, "direct_answer_generation"):
        response = llm.invoke(
            [
                SystemMessage(content=render_prompt(DIRECT_PROMPT_NAME, query=contextualized_query)),
                HumanMessage(content=contextualized_query),
            ]
        )
    answer = str(response.content or "").strip()
    interaction = record_interaction(
        query=query,
        contextualized_query=contextualized_query,
        answer=answer,
        contexts=[],
        top_k=top_k,
        score_threshold=score_threshold,
        route=route.route,
        route_reasoning=route.reasoning,
        session_id=session_id,
    )
    trace("Answer generation completed", logger)
    return AiResponse(
        answer=answer,
        query=query,
        contextualized_query=contextualized_query,
        contexts=[],
        route=route.route,
        route_reasoning=route.reasoning,
        session_id=interaction["session_id"],
        interaction_id=interaction["interaction_id"],
    )


def _resolve_route(
    query: str,
    *,
    llm,
    document_ids: list[str] | None,
    tags: list[str] | None,
    retrieval_enabled: bool,
    web_search_enabled: bool,
    route_mode: str | None,
) -> RouteDecision:
    selected_mode = (route_mode or "auto").strip().lower()
    if selected_mode in {"retrieval", "web_search", "direct"}:
        route = RouteDecision(route=selected_mode, reasoning="User selected this route.")
    elif (document_ids or tags) and retrieval_enabled:
        route = RouteDecision(route="retrieval", reasoning="Chat has document or tag filters attached.")
    else:
        route = route_query(query, llm=llm)

    if route.route == "web_search" and not web_search_enabled:
        fallback = "retrieval" if retrieval_enabled else "direct"
        return RouteDecision(route=fallback, reasoning="Web search is disabled for this request.")
    if route.route == "retrieval" and not retrieval_enabled:
        return RouteDecision(route="direct", reasoning="Retrieval is disabled for this request.")

    return route


def generate_response(query: str) -> str:
    """Backward-compatible helper that returns only the final answer text."""
    return answer_question(query).answer
