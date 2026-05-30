from dataclasses import dataclass, field
from typing import Any

from app.core.config import (
    TAVILY_API_KEY,
    TAVILY_INCLUDE_ANSWER,
    TAVILY_INCLUDE_RAW_CONTENT,
    TAVILY_MAX_RESULTS,
    TAVILY_SEARCH_DEPTH,
)
from app.core.logging import get_logger, log_timing, trace
from app.services.retrieval import RetrievedContext

logger = get_logger(__name__)


@dataclass
class WebSearchResponse:
    query: str
    answer: str | None = None
    contexts: list[RetrievedContext] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def sources(self) -> list[dict[str, Any]]:
        return [
            {
                "source": context.source_label,
                "score": context.score,
                "metadata": context.metadata,
            }
            for context in self.contexts
        ]


def _client():
    if not TAVILY_API_KEY:
        logger.error("tavily client requested without api key")
        raise ValueError("TAVILY_API_KEY is not configured in .env")

    from tavily import TavilyClient

    logger.debug("tavily client creating")
    return TavilyClient(api_key=TAVILY_API_KEY)


def _result_content(result: dict[str, Any]) -> str:
    parts = []
    title = str(result.get("title") or "").strip()
    url = str(result.get("url") or "").strip()
    content = str(
        result.get("content")
        or result.get("raw_content")
        or result.get("snippet")
        or ""
    ).strip()

    if title:
        parts.append(f"Title: {title}")
    if url:
        parts.append(f"URL: {url}")
    if content:
        parts.append(content)

    return "\n".join(parts).strip()


def _to_context(result: dict[str, Any], rank: int) -> RetrievedContext:
    title = str(result.get("title") or "").strip()
    url = str(result.get("url") or "").strip()
    score = result.get("score")
    metadata = {
        "source_type": "web",
        "title": title,
        "url": url,
        "rank": rank,
        "filename": title or url or f"Web result {rank}",
    }

    return RetrievedContext(
        content=_result_content(result),
        metadata=metadata,
        score=float(score) if isinstance(score, (int, float)) else None,
    )


def format_web_context(contexts: list[RetrievedContext], tavily_answer: str | None = None) -> str:
    sections = []
    if tavily_answer:
        sections.append(f"Tavily summary:\n{tavily_answer.strip()}")

    for index, context in enumerate(contexts, start=1):
        url = context.metadata.get("url") or ""
        sections.append(
            "\n".join(
                [
                    f"[{index}] Source: {context.source_label}",
                    f"URL: {url}",
                    f"Score: {context.score if context.score is not None else 'n/a'}",
                    context.content,
                ]
            )
        )

    return "\n\n".join(sections) if sections else "No web results were returned."


def search_web(
    query: str,
    *,
    max_results: int = TAVILY_MAX_RESULTS,
    search_depth: str = TAVILY_SEARCH_DEPTH,
) -> WebSearchResponse:
    trace("Web search started", logger)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    try:
        with log_timing(logger, "tavily_search", max_results=max_results, search_depth=search_depth):
            response = _client().search(
                query=query.strip(),
                search_depth=search_depth,
                max_results=max_results,
                include_answer=TAVILY_INCLUDE_ANSWER,
                include_raw_content=TAVILY_INCLUDE_RAW_CONTENT,
            )
    except Exception as exc:
        logger.exception("web search failed")
        trace("Web search failed", logger)
        raise ValueError(
            "Web search failed. Check TAVILY_API_KEY and Tavily connectivity."
        ) from exc

    if not isinstance(response, dict):
        logger.error("web search returned unexpected response", extra={"event": {"response_type": type(response).__name__}})
        raise ValueError("Web search returned an unexpected response format.")

    results = response.get("results") or []
    contexts = [
        _to_context(result, rank=index)
        for index, result in enumerate(results, start=1)
        if _result_content(result)
    ]

    result = WebSearchResponse(
        query=query.strip(),
        answer=response.get("answer"),
        contexts=contexts,
        raw=response,
    )
    logger.info("web search completed", extra={"event": {"result_count": len(results), "context_count": len(contexts)}})
    trace(f"Web search completed with {len(contexts)} context(s)", logger)
    return result


def web_search(query: str) -> str:
    """Backward-compatible helper returning Tavily's answer or formatted results."""
    result = search_web(query)
    return result.answer or format_web_context(result.contexts)


def websearc(query: str) -> str:
    """Deprecated typo-compatible wrapper."""
    return web_search(query)
