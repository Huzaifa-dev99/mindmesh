from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchAny

from app.core.config import METADATA_PAYLOAD_KEY, RETRIEVER_SCORE_THRESHOLD, RETRIEVER_TOP_K
from app.core.logging import get_logger, log_timing, trace

logger = get_logger(__name__)


@dataclass
class RetrievedContext:
    content: str
    metadata: dict
    score: float | None = None

    @property
    def source_label(self) -> str:
        if self.metadata.get("source_type") == "web":
            return self.metadata.get("title") or self.metadata.get("url") or "web result"

        filename = self.metadata.get("filename") or "unknown"
        page_number = self.metadata.get("page_number")
        if page_number:
            return f"{filename} p. {page_number}"

        version = self.metadata.get("document_version")
        if version:
            return f"{filename} ({version})"

        return filename

    @property
    def reference_metadata(self) -> dict:
        if self.metadata.get("source_type") == "web":
            return {
                "title": self.metadata.get("title"),
                "url": self.metadata.get("url"),
            }

        return {
            "filename": self.metadata.get("filename"),
            "page_number": self.metadata.get("page_number"),
            "file_type": self.metadata.get("file_type"),
        }


def retrieve_context(
    query: str,
    top_k: int = RETRIEVER_TOP_K,
    score_threshold: float = RETRIEVER_SCORE_THRESHOLD,
    document_ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[RetrievedContext]:
    trace("Vector retrieval started", logger)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    from app.core.clients import get_qdrant_vector_store

    qdrant_vs = get_qdrant_vector_store()
    qdrant_filter = _retrieval_filter(document_ids=document_ids, tags=tags)
    with log_timing(
        logger,
        "qdrant_similarity_search",
        top_k=top_k,
        score_threshold=score_threshold,
        document_filter_count=len(document_ids or []),
        tag_filter_count=len(tags or []),
    ):
        results = qdrant_vs.similarity_search_with_score(
            query.strip(),
            k=top_k,
            filter=qdrant_filter,
            score_threshold=score_threshold if score_threshold > 0 else None,
        )
    contexts = [
        RetrievedContext(
            content=document.page_content,
            metadata=dict(document.metadata or {}),
            score=score,
        )
        for document, score in results
        if score_threshold <= 0 or score >= score_threshold
    ]

    logger.info(
        "vector retrieval completed",
        extra={"event": {"result_count": len(results), "context_count": len(contexts)}},
    )
    trace(f"Vector retrieval completed with {len(contexts)} context(s)", logger)
    return contexts


def _metadata_field(name: str) -> str:
    return f"{METADATA_PAYLOAD_KEY}.{name}"


def _retrieval_filter(
    *,
    document_ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> Filter | None:
    conditions = []
    cleaned_document_ids = [doc_id for doc_id in (document_ids or []) if doc_id]
    cleaned_tags = [tag for tag in (tags or []) if tag]

    if cleaned_document_ids:
        conditions.append(
            FieldCondition(
                key=_metadata_field("document_id"),
                match=MatchAny(any=cleaned_document_ids),
            )
        )
    if cleaned_tags:
        conditions.append(
            FieldCondition(
                key=_metadata_field("tags"),
                match=MatchAny(any=cleaned_tags),
            )
        )

    return Filter(must=conditions) if conditions else None


def format_context(contexts: list[RetrievedContext]) -> str:
    if not contexts:
        return "No relevant context was retrieved."

    formatted = []
    for index, context in enumerate(contexts, start=1):
        formatted.append(
            "\n".join(
                [
                    f"[{index}] Source: {context.source_label}",
                    f"Score: {context.score}",
                    context.content,
                ]
            )
        )

    return "\n\n".join(formatted)


def retrieve_text(query: str):
    """Backward-compatible wrapper for older imports."""
    return retrieve_context(query)
