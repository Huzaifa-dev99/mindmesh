from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.core.database import connect, ensure_database
from app.core.logging import get_logger, log_timing, trace
from app.core.serialization import serialize_datetime
from app.services.ai_settings import active_model_name

logger = get_logger(__name__)

def _session_title(query: str) -> str:
    title = " ".join(query.strip().split())
    return title[:80] or "Chat session"


def _uuid(value: str | UUID | None) -> UUID:
    if value is None:
        return uuid4()
    if isinstance(value, UUID):
        return value

    return UUID(value)


def _public_metadata(metadata: dict) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if key not in {"_id", "_collection_name"}
    }


def _reference_metadata(metadata: dict) -> dict:
    if metadata.get("source_type") == "web":
        keys = ("title", "url")
    else:
        keys = ("filename", "page_number", "file_type")

    return {
        key: metadata.get(key)
        for key in keys
        if metadata.get(key) not in (None, "")
    }


def _vector_id(metadata: dict) -> str | None:
    value = metadata.get("_id")
    return str(value) if value not in (None, "") else None


def _source_payload(contexts: list) -> list[dict]:
    sources = []
    for context in contexts:
        metadata = dict(context.metadata or {})
        sources.append(
            {
                "source": context.source_label,
                "score": context.score,
                "vector_id": _vector_id(metadata),
                "collection_name": metadata.get("_collection_name"),
                "metadata": _reference_metadata(metadata),
            }
        )

    return sources


def _content_preview(content: str, limit: int = 1200) -> str:
    return " ".join((content or "").split())[:limit]


def _document_id_for_context(cursor, metadata: dict) -> str | None:
    if metadata.get("source_type") == "web":
        return None

    vector_id = _vector_id(metadata)
    if vector_id:
        cursor.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE point_ids @> %s
            ORDER BY indexed_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
            """,
            (Jsonb([vector_id]),),
        )
        row = cursor.fetchone()
        if row:
            return row["id"]

    filename = metadata.get("filename")
    document_version = metadata.get("document_version")
    if not filename:
        return None

    if document_version:
        cursor.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE filename = %s
              AND document_version = %s
            ORDER BY indexed_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
            """,
            (filename, document_version),
        )
    else:
        cursor.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE filename = %s
            ORDER BY indexed_at DESC NULLS LAST, updated_at DESC
            LIMIT 1
            """,
            (filename,),
        )

    row = cursor.fetchone()
    return row["id"] if row else None


def _source_score(source: dict) -> float | None:
    score = source.get("score")
    return float(score) if score is not None else None


def _record_retrieved_chunks(
    cursor,
    *,
    interaction_id: UUID,
    session_id: UUID,
    contexts: list,
) -> None:
    for rank, context in enumerate(contexts, start=1):
        metadata = dict(context.metadata or {})
        cursor.execute(
            """
            INSERT INTO rag.chat_retrieved_chunks (
                id,
                interaction_id,
                session_id,
                rank,
                document_id,
                vector_id,
                collection_name,
                source,
                score,
                content_preview,
                metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (interaction_id, rank) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                vector_id = EXCLUDED.vector_id,
                collection_name = EXCLUDED.collection_name,
                source = EXCLUDED.source,
                score = EXCLUDED.score,
                content_preview = EXCLUDED.content_preview,
                metadata = EXCLUDED.metadata
            """,
            (
                uuid4(),
                interaction_id,
                session_id,
                rank,
                _document_id_for_context(cursor, metadata),
                _vector_id(metadata),
                metadata.get("_collection_name"),
                context.source_label,
                float(context.score) if context.score is not None else None,
                _content_preview(context.content),
                Jsonb(_public_metadata(metadata)),
            ),
        )


def backfill_retrieved_chunks_from_sources() -> int:
    """Populate chunk analytics for interactions recorded before chunk logging existed."""
    trace("Chat retrieval backfill started", logger)
    ensure_database()
    inserted = 0

    with log_timing(logger, "chat_retrieval_backfill"):
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        interaction.id,
                        interaction.session_id,
                        interaction.sources
                    FROM rag.chat_interactions AS interaction
                    WHERE jsonb_array_length(interaction.sources) > 0
                      AND NOT EXISTS (
                          SELECT 1
                          FROM rag.chat_retrieved_chunks AS chunk
                          WHERE chunk.interaction_id = interaction.id
                      )
                    ORDER BY interaction.created_at ASC
                    """
                )
                interactions = cursor.fetchall()

                for interaction in interactions:
                    for rank, source in enumerate(interaction["sources"] or [], start=1):
                        metadata = dict(source.get("metadata") or {})
                        vector_id = source.get("vector_id") or _vector_id(metadata)
                        if vector_id:
                            metadata["_id"] = vector_id
                        collection_name = (
                            source.get("collection_name") or metadata.get("_collection_name")
                        )
                        if collection_name:
                            metadata["_collection_name"] = collection_name

                        cursor.execute(
                            """
                            INSERT INTO rag.chat_retrieved_chunks (
                                id,
                                interaction_id,
                                session_id,
                                rank,
                                document_id,
                                vector_id,
                                collection_name,
                                source,
                                score,
                                content_preview,
                                metadata
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (interaction_id, rank) DO NOTHING
                            """,
                            (
                                uuid4(),
                                interaction["id"],
                                interaction["session_id"],
                                rank,
                                _document_id_for_context(cursor, metadata),
                                vector_id,
                                collection_name,
                                source.get("source") or "unknown",
                                _source_score(source),
                                "",
                                Jsonb(_public_metadata(metadata)),
                            ),
                        )
                        inserted += cursor.rowcount

            conn.commit()

    logger.info("chat retrieval backfill completed", extra={"event": {"inserted": inserted}})
    trace(f"Chat retrieval backfill completed with {inserted} chunk(s)", logger)
    return inserted


def record_interaction(
    *,
    query: str,
    answer: str,
    contexts: list,
    top_k: int,
    score_threshold: float,
    contextualized_query: str | None = None,
    route: str | None = None,
    route_reasoning: str | None = None,
    session_id: str | UUID | None = None,
) -> dict:
    trace("Chat interaction recording started", logger)
    ensure_database()
    session_uuid = _uuid(session_id)
    interaction_uuid = uuid4()
    sources = _source_payload(contexts)

    with log_timing(
        logger,
        "chat_interaction_record",
        context_count=len(contexts),
        route=route,
        has_existing_session=bool(session_id),
    ):
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag.chat_sessions (id, title)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                    """,
                    (session_uuid, _session_title(query)),
                )
                cursor.execute(
                    """
                    INSERT INTO rag.chat_interactions (
                        id,
                        session_id,
                        query,
                        contextualized_query,
                        answer,
                        top_k,
                        score_threshold,
                        context_count,
                        sources,
                        route,
                        route_reasoning,
                        model
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, created_at
                    """,
                    (
                        interaction_uuid,
                        session_uuid,
                        query,
                        contextualized_query,
                        answer,
                        top_k,
                        score_threshold,
                        len(contexts),
                        Jsonb(sources),
                        route,
                        route_reasoning,
                        active_model_name(),
                    ),
                )
                row = cursor.fetchone()
                _record_retrieved_chunks(
                    cursor,
                    interaction_id=interaction_uuid,
                    session_id=session_uuid,
                    contexts=contexts,
                )
            conn.commit()

    result = {
        "interaction_id": str(row["id"]),
        "session_id": str(row["session_id"]),
        "created_at": serialize_datetime(row["created_at"]),
    }
    logger.info(
        "chat interaction recorded",
        extra={
            "event": {
                "session_id": result["session_id"],
                "interaction_id": result["interaction_id"],
                "context_count": len(contexts),
                "route": route,
            }
        },
    )
    trace("Chat interaction recording completed", logger)
    return result


def list_sessions() -> list[dict]:
    trace("Chat session listing started", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    session.id,
                    session.title,
                    session.created_at,
                    session.updated_at,
                    COUNT(interaction.id) AS interaction_count
                FROM rag.chat_sessions AS session
                LEFT JOIN rag.chat_interactions AS interaction
                    ON interaction.session_id = session.id
                GROUP BY session.id
                ORDER BY session.updated_at DESC
                """
            )
            sessions = [
                {
                    "id": str(row["id"]),
                    "title": row["title"],
                    "created_at": serialize_datetime(row["created_at"]),
                    "updated_at": serialize_datetime(row["updated_at"]),
                    "interaction_count": row["interaction_count"],
                }
                for row in cursor.fetchall()
            ]
    logger.info("chat session listing completed", extra={"event": {"session_count": len(sessions)}})
    trace(f"Chat session listing completed with {len(sessions)} session(s)", logger)
    return sessions


def list_interactions(session_id: str | UUID) -> list[dict]:
    trace("Chat interaction listing started", logger)
    ensure_database()
    session_uuid = _uuid(session_id)

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.chat_interactions
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_uuid,),
            )
            interactions = [
                {
                    "id": str(row["id"]),
                    "session_id": str(row["session_id"]),
                    "query": row["query"],
                    "contextualized_query": row.get("contextualized_query"),
                    "answer": row["answer"],
                    "top_k": row["top_k"],
                    "score_threshold": row["score_threshold"],
                    "context_count": row["context_count"],
                    "sources": row["sources"] or [],
                    "route": row.get("route"),
                    "route_reasoning": row.get("route_reasoning"),
                    "model": row["model"],
                    "created_at": serialize_datetime(row["created_at"]),
                }
                for row in cursor.fetchall()
            ]
    logger.info(
        "chat interaction listing completed",
        extra={"event": {"session_id": str(session_uuid), "interaction_count": len(interactions)}},
    )
    trace(f"Chat interaction listing completed with {len(interactions)} interaction(s)", logger)
    return interactions
