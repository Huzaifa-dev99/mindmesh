from collections import Counter
from typing import Any

from app.core.database import connect, ensure_database
from app.core.logging import get_logger, log_timing, trace
from app.core.serialization import serialize_datetime
from app.services.document_registry import FAILED, INDEXED, NOT_INDEXED, list_documents

logger = get_logger(__name__)

def _sorted_counts(counter: Counter, label_key: str) -> list[dict[str, Any]]:
    return [
        {label_key: label, "count": count}
        for label, count in counter.most_common()
    ]


def _document_status(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {
        INDEXED: "Indexed",
        NOT_INDEXED: "Not indexed",
        FAILED: "Failed",
    }
    counter = Counter(document.get("status") or "unknown" for document in documents)
    return [
        {
            "status": status,
            "label": labels.get(status, status.replace("_", " ").title()),
            "count": counter.get(status, 0),
        }
        for status in (INDEXED, NOT_INDEXED, FAILED)
    ]


def _document_tags(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter()
    for document in documents:
        tags = document.get("tags") or []
        if not tags:
            counter["untagged"] += 1
            continue

        for tag in tags:
            counter[str(tag)] += 1

    return _sorted_counts(counter, "tag")


def _document_versions(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(
        document.get("document_version") or "unversioned"
        for document in documents
    )
    return _sorted_counts(counter, "version")


def _storage_summary(documents: list[dict[str, Any]]) -> dict[str, Any]:
    sizes = [int(document.get("size") or 0) for document in documents]
    total_bytes = sum(sizes)
    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "average_document_mb": (
            round((total_bytes / len(documents)) / (1024 * 1024), 2)
            if documents
            else 0
        ),
        "largest_documents": sorted(
            [
                {
                    "filename": document.get("filename") or "document",
                    "document_version": document.get("document_version"),
                    "size_mb": round(int(document.get("size") or 0) / (1024 * 1024), 2),
                    "status": document.get("status"),
                }
                for document in documents
            ],
            key=lambda item: item["size_mb"],
            reverse=True,
        )[:5],
    }


def _recent_failed_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [document for document in documents if document.get("status") == FAILED]
    rows = sorted(
        failed,
        key=lambda item: item.get("updated_at") or item.get("last_seen_at") or "",
        reverse=True,
    )
    return [
        {
            "id": document.get("id"),
            "filename": document.get("filename"),
            "document_version": document.get("document_version"),
            "last_error": document.get("last_error"),
            "updated_at": document.get("updated_at"),
        }
        for document in rows[:5]
    ]


def _chat_totals(cursor) -> dict[str, Any]:
    cursor.execute("SELECT COUNT(*) AS count FROM rag.chat_sessions")
    total_sessions = cursor.fetchone()["count"]

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_queries,
            COALESCE(SUM(context_count), 0) AS total_contexts,
            COALESCE(AVG(context_count), 0) AS average_contexts
        FROM rag.chat_interactions
        """
    )
    interaction = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_retrieved_chunks,
            COALESCE(AVG(score), 0) AS average_score
        FROM rag.chat_retrieved_chunks
        """
    )
    retrieval = cursor.fetchone()

    return {
        "total_chat_sessions": total_sessions,
        "total_queries": interaction["total_queries"],
        "total_contexts_returned": interaction["total_contexts"],
        "average_contexts_per_query": round(float(interaction["average_contexts"]), 2),
        "total_retrieved_chunks_logged": retrieval["total_retrieved_chunks"],
        "average_retrieval_score": round(float(retrieval["average_score"]), 4),
    }


def _top_referenced_documents(cursor, limit: int) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            COALESCE(document.id, chunk.document_id) AS document_id,
            COALESCE(document.filename, chunk.source, 'unknown') AS filename,
            COALESCE(
                document.document_version,
                chunk.metadata->>'document_version',
                ''
            ) AS document_version,
            COUNT(*) AS reference_count,
            COUNT(DISTINCT chunk.interaction_id) AS query_count,
            COALESCE(AVG(chunk.score), 0) AS average_score,
            MAX(chunk.created_at) AS last_referenced_at
        FROM rag.chat_retrieved_chunks AS chunk
        LEFT JOIN rag.documents AS document
            ON document.id = chunk.document_id
        GROUP BY
            COALESCE(document.id, chunk.document_id),
            COALESCE(document.filename, chunk.source, 'unknown'),
            COALESCE(document.document_version, chunk.metadata->>'document_version', '')
        ORDER BY reference_count DESC, query_count DESC, filename ASC
        LIMIT %s
        """,
        (limit,),
    )
    return [
        {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "document_version": row["document_version"] or None,
            "reference_count": row["reference_count"],
            "query_count": row["query_count"],
            "average_score": round(float(row["average_score"]), 4),
            "last_referenced_at": serialize_datetime(row["last_referenced_at"]),
        }
        for row in cursor.fetchall()
    ]


def _recent_queries(cursor, limit: int = 8) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT
            interaction.id,
            interaction.session_id,
            interaction.query,
            interaction.contextualized_query,
            interaction.context_count,
            interaction.created_at,
            COALESCE(COUNT(chunk.id), 0) AS retrieved_chunk_count
        FROM rag.chat_interactions AS interaction
        LEFT JOIN rag.chat_retrieved_chunks AS chunk
            ON chunk.interaction_id = interaction.id
        GROUP BY interaction.id
        ORDER BY interaction.created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [
        {
            "id": str(row["id"]),
            "session_id": str(row["session_id"]),
            "query": row["query"],
            "contextualized_query": row["contextualized_query"],
            "context_count": row["context_count"],
            "retrieved_chunk_count": row["retrieved_chunk_count"],
            "created_at": serialize_datetime(row["created_at"]),
        }
        for row in cursor.fetchall()
    ]


def dashboard_analytics(top_limit: int = 5) -> dict[str, Any]:
    trace("Dashboard analytics calculation started", logger)
    ensure_database()
    from app.services.chat_history import backfill_retrieved_chunks_from_sources

    with log_timing(logger, "dashboard_analytics", top_limit=top_limit):
        backfill_retrieved_chunks_from_sources()
        documents = list_documents()
        status_counts = Counter(document.get("status") or "unknown" for document in documents)
        indexed_chunks = sum(int(document.get("chunk_count") or 0) for document in documents)

        with connect() as conn:
            with conn.cursor() as cursor:
                chat_totals = _chat_totals(cursor)
                top_referenced_documents = _top_referenced_documents(cursor, top_limit)
                recent_queries = _recent_queries(cursor)

    totals = {
        "total_documents_uploaded": len(documents),
        "total_documents_indexed": status_counts.get(INDEXED, 0),
        "documents_not_indexed": status_counts.get(NOT_INDEXED, 0),
        "documents_failed": status_counts.get(FAILED, 0),
        "total_indexed_chunks": indexed_chunks,
        **chat_totals,
    }

    result = {
        "totals": totals,
        "document_status": _document_status(documents),
        "document_tags": _document_tags(documents),
        "document_versions": _document_versions(documents),
        "top_referenced_documents": top_referenced_documents,
        "recent_queries": recent_queries,
        "recent_failed_documents": _recent_failed_documents(documents),
        "storage": _storage_summary(documents),
        "retrieval": {
            "top_document_limit": top_limit,
            "has_retrieval_log": totals["total_retrieved_chunks_logged"] > 0,
        },
    }
    logger.info(
        "dashboard analytics calculated",
        extra={
            "event": {
                "document_count": len(documents),
                "indexed_chunks": indexed_chunks,
                "total_queries": totals["total_queries"],
            }
        },
    )
    trace("Dashboard analytics calculation completed", logger)
    return result
