import json
from pathlib import PurePosixPath
from typing import Any

from psycopg.types.json import Jsonb

from app.core.config import DOCUMENT_REGISTRY_PATH, S3_BUCKET
from app.core.database import connect, ensure_database
from app.core.logging import get_logger, trace
from app.core.serialization import serialize_datetime

INDEXED = "indexed"
NOT_INDEXED = "not_indexed"
FAILED = "failed"

logger = get_logger(__name__)


def document_id(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"

def _row_to_document(row: dict | None) -> dict:
    if not row:
        return {}

    return {
        "id": row["id"],
        "bucket": row["bucket"],
        "key": row["object_key"],
        "filename": row["filename"],
        "logical_filename": row.get("logical_filename"),
        "document_version": row.get("document_version"),
        "tags": row.get("tags") or [],
        "lexical_hash": row.get("lexical_hash"),
        "status": row["status"],
        "etag": row.get("etag"),
        "size": row.get("size_bytes"),
        "last_modified": serialize_datetime(row.get("last_modified")),
        "last_seen_at": serialize_datetime(row.get("last_seen_at")),
        "indexed_at": serialize_datetime(row.get("indexed_at")),
        "chunk_count": row.get("chunk_count") or 0,
        "point_ids": row.get("point_ids") or [],
        "last_error": row.get("last_error"),
        "created_at": serialize_datetime(row.get("created_at")),
        "updated_at": serialize_datetime(row.get("updated_at")),
    }


def _object_signature(item: dict[str, Any]) -> dict:
    return {
        "etag": str(item.get("ETag") or "").strip('"'),
        "size": item.get("Size"),
        "last_modified": item.get("LastModified"),
    }


def _fetch_document(conn, doc_id: str) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM rag.documents WHERE id = %s", (doc_id,))
        return cursor.fetchone()


def get_documents(doc_ids: list[str]) -> list[dict]:
    if not doc_ids:
        return []

    ensure_database()
    logger.debug("document registry lookup started", extra={"event": {"document_count": len(doc_ids)}})
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.documents
                WHERE id = ANY(%s)
                ORDER BY filename ASC
                """,
                (doc_ids,),
            )
            documents = [_row_to_document(row) for row in cursor.fetchall()]

    logger.info("document registry lookup completed", extra={"event": {"document_count": len(documents)}})
    return documents


def find_document_versions(bucket: str, logical_filename: str) -> list[dict]:
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.documents
                WHERE bucket = %s
                  AND logical_filename = %s
                ORDER BY document_version DESC NULLS LAST, created_at DESC
                """,
                (bucket, logical_filename),
            )
            return [_row_to_document(row) for row in cursor.fetchall()]


def find_document_by_lexical_hash(bucket: str, lexical_hash: str) -> dict | None:
    if not lexical_hash:
        return None

    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.documents
                WHERE bucket = %s
                  AND lexical_hash = %s
                ORDER BY indexed_at DESC NULLS LAST, created_at ASC
                LIMIT 1
                """,
                (bucket, lexical_hash),
            )
            return _row_to_document(cursor.fetchone())


def list_documents() -> list[dict]:
    trace("Document registry listing started", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.documents
                ORDER BY last_seen_at DESC, filename ASC
                """
            )
            documents = [_row_to_document(row) for row in cursor.fetchall()]

    logger.info("document registry listing completed", extra={"event": {"document_count": len(documents)}})
    trace(f"Document registry listing completed with {len(documents)} document(s)", logger)
    return documents


def get_document(doc_id: str) -> dict:
    ensure_database()
    with connect() as conn:
        return _row_to_document(_fetch_document(conn, doc_id))


def sync_documents(s3_objects: list[dict], bucket: str = S3_BUCKET) -> list[dict]:
    trace(f"Document registry sync started for {len(s3_objects)} object(s)", logger)
    ensure_database()
    synced = []

    with connect() as conn:
        for item in s3_objects:
            key = item["Key"]
            doc_id = document_id(bucket, key)
            signature = _object_signature(item)
            filename = PurePosixPath(key).name
            existing = _fetch_document(conn, doc_id)
            display_filename = existing.get("filename") if existing else filename
            existing_signature = {
                "etag": existing.get("etag") if existing else None,
                "size": existing.get("size_bytes") if existing else None,
                "last_modified": existing.get("last_modified") if existing else None,
            }
            has_changed = bool(existing) and existing_signature != signature
            status = NOT_INDEXED if not existing or has_changed else existing["status"]

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag.documents (
                        id,
                        bucket,
                        object_key,
                        filename,
                        logical_filename,
                        document_version,
                        tags,
                        lexical_hash,
                        status,
                        etag,
                        size_bytes,
                        last_modified,
                        last_seen_at,
                        indexed_at,
                        chunk_count,
                        point_ids,
                        last_error
                    )
                    VALUES (
                        %(id)s,
                        %(bucket)s,
                        %(object_key)s,
                        %(filename)s,
                        %(logical_filename)s,
                        %(document_version)s,
                        %(tags)s,
                        %(lexical_hash)s,
                        %(status)s,
                        %(etag)s,
                        %(size)s,
                        %(last_modified)s,
                        NOW(),
                        %(indexed_at)s,
                        %(chunk_count)s,
                        %(point_ids)s,
                        %(last_error)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        bucket = EXCLUDED.bucket,
                        object_key = EXCLUDED.object_key,
                        filename = EXCLUDED.filename,
                        logical_filename = EXCLUDED.logical_filename,
                        document_version = EXCLUDED.document_version,
                        tags = EXCLUDED.tags,
                        lexical_hash = EXCLUDED.lexical_hash,
                        status = EXCLUDED.status,
                        etag = EXCLUDED.etag,
                        size_bytes = EXCLUDED.size_bytes,
                        last_modified = EXCLUDED.last_modified,
                        last_seen_at = NOW(),
                        indexed_at = EXCLUDED.indexed_at,
                        chunk_count = EXCLUDED.chunk_count,
                        point_ids = EXCLUDED.point_ids,
                        last_error = EXCLUDED.last_error,
                        updated_at = NOW()
                    RETURNING *
                    """,
                    {
                        "id": doc_id,
                        "bucket": bucket,
                        "object_key": key,
                        "filename": display_filename,
                        "logical_filename": existing.get("logical_filename")
                        if existing
                        else display_filename.lower(),
                        "document_version": existing.get("document_version")
                        if existing
                        else None,
                        "tags": Jsonb(existing.get("tags") or []) if existing else Jsonb([]),
                        "lexical_hash": existing.get("lexical_hash") if existing else None,
                        "status": status,
                        "etag": signature["etag"],
                        "size": signature["size"],
                        "last_modified": signature["last_modified"],
                        "indexed_at": None
                        if has_changed or not existing
                        else existing.get("indexed_at"),
                        "chunk_count": 0
                        if has_changed or not existing
                        else existing.get("chunk_count", 0),
                        "point_ids": Jsonb([])
                        if has_changed or not existing
                        else Jsonb(existing.get("point_ids") or []),
                        "last_error": None
                        if has_changed or not existing
                        else existing.get("last_error"),
                    },
                )
                synced.append(_row_to_document(cursor.fetchone()))

        conn.commit()

    logger.info(
        "document registry sync completed",
        extra={"event": {"object_count": len(s3_objects), "document_count": len(synced)}},
    )
    trace(f"Document registry sync completed with {len(synced)} document(s)", logger)
    return synced


def is_indexed(doc_id: str) -> bool:
    return get_document(doc_id).get("status") == INDEXED


def mark_indexed(doc_id: str, chunk_count: int, point_ids: list[str]) -> None:
    trace("Document index status update started", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.documents
                SET
                    status = %s,
                    indexed_at = NOW(),
                    chunk_count = %s,
                    point_ids = %s,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (INDEXED, chunk_count, Jsonb([str(point_id) for point_id in point_ids]), doc_id),
            )
        conn.commit()
    logger.info(
        "document marked indexed",
        extra={
            "event": {
                "document_id": doc_id,
                "chunk_count": chunk_count,
                "point_count": len(point_ids),
            }
        },
    )
    trace("Document index status update completed", logger)


def mark_not_indexed(doc_id: str, error: str | None = None) -> None:
    trace("Document index rollback started", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.documents
                SET
                    status = %s,
                    last_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (NOT_INDEXED, error, doc_id),
            )
        conn.commit()
    logger.info(
        "document marked not indexed",
        extra={"event": {"document_id": doc_id, "has_error": bool(error)}},
    )
    trace("Document index rollback completed", logger)


def register_uploaded_document(
    *,
    doc_id: str,
    bucket: str,
    key: str,
    filename: str,
    logical_filename: str,
    document_version: str,
    tags: list[str],
    lexical_hash: str,
    etag: str | None,
    size: int | None,
    last_modified,
) -> dict:
    trace("Uploaded document registration started", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rag.documents (
                    id,
                    bucket,
                    object_key,
                    filename,
                    logical_filename,
                    document_version,
                    tags,
                    lexical_hash,
                    status,
                    etag,
                    size_bytes,
                    last_modified,
                    last_seen_at,
                    indexed_at,
                    chunk_count,
                    point_ids,
                    last_error
                )
                VALUES (
                    %(id)s,
                    %(bucket)s,
                    %(object_key)s,
                    %(filename)s,
                    %(logical_filename)s,
                    %(document_version)s,
                    %(tags)s,
                    %(lexical_hash)s,
                    %(status)s,
                    %(etag)s,
                    %(size)s,
                    %(last_modified)s,
                    NOW(),
                    NULL,
                    0,
                    '[]'::jsonb,
                    NULL
                )
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    logical_filename = EXCLUDED.logical_filename,
                    document_version = EXCLUDED.document_version,
                    tags = EXCLUDED.tags,
                    lexical_hash = EXCLUDED.lexical_hash,
                    status = EXCLUDED.status,
                    etag = EXCLUDED.etag,
                    size_bytes = EXCLUDED.size_bytes,
                    last_modified = EXCLUDED.last_modified,
                    last_seen_at = NOW(),
                    indexed_at = NULL,
                    chunk_count = 0,
                    point_ids = '[]'::jsonb,
                    last_error = NULL,
                    updated_at = NOW()
                RETURNING *
                """,
                {
                    "id": doc_id,
                    "bucket": bucket,
                    "object_key": key,
                    "filename": filename,
                    "logical_filename": logical_filename,
                    "document_version": document_version,
                    "tags": Jsonb(tags),
                    "lexical_hash": lexical_hash,
                    "status": NOT_INDEXED,
                    "etag": etag,
                    "size": size,
                    "last_modified": last_modified,
                },
            )
            document = _row_to_document(cursor.fetchone())
        conn.commit()

    logger.info(
        "uploaded document registered",
        extra={"event": {"document_id": doc_id, "filename": filename, "version": document_version}},
    )
    trace("Uploaded document registration completed", logger)
    return document


def clear_document_vectors(doc_ids: list[str]) -> list[dict]:
    if not doc_ids:
        return []

    trace(f"Document vector state clearing started for {len(doc_ids)} document(s)", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.documents
                SET
                    status = %s,
                    indexed_at = NULL,
                    chunk_count = 0,
                    point_ids = '[]'::jsonb,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = ANY(%s)
                RETURNING *
                """,
                (NOT_INDEXED, doc_ids),
            )
            documents = [_row_to_document(row) for row in cursor.fetchall()]
        conn.commit()

    logger.info("document vector state cleared", extra={"event": {"document_count": len(documents)}})
    trace(f"Document vector state clearing completed for {len(documents)} document(s)", logger)
    return documents


def delete_documents(doc_ids: list[str]) -> int:
    if not doc_ids:
        return 0

    trace(f"Document registry deletion started for {len(doc_ids)} document(s)", logger)
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM rag.documents WHERE id = ANY(%s)",
                (doc_ids,),
            )
            deleted = cursor.rowcount
        conn.commit()

    logger.info("document registry deletion completed", extra={"event": {"requested": len(doc_ids), "deleted": deleted}})
    trace(f"Document registry deletion completed with {deleted} document(s) deleted", logger)
    return deleted


def migrate_json_registry() -> int:
    """Import the legacy JSON registry into Postgres once, if it exists."""
    trace("Legacy document registry migration check started", logger)
    ensure_database()
    if not DOCUMENT_REGISTRY_PATH.exists():
        logger.info("legacy document registry migration skipped; file not found")
        trace("Legacy document registry migration skipped", logger)
        return 0

    logger.info("legacy document registry file loading", extra={"event": {"path": str(DOCUMENT_REGISTRY_PATH)}})
    with DOCUMENT_REGISTRY_PATH.open("r", encoding="utf-8") as file:
        registry = json.load(file)

    records = registry.get("documents", {}).values()
    migrated = 0

    with connect() as conn:
        for record in records:
            doc_id = record.get("id")
            bucket = record.get("bucket")
            key = record.get("key")
            if not doc_id or not bucket or not key:
                continue

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag.documents (
                        id,
                        bucket,
                        object_key,
                        filename,
                        logical_filename,
                        document_version,
                        tags,
                        lexical_hash,
                        status,
                        etag,
                        size_bytes,
                        last_modified,
                        last_seen_at,
                        indexed_at,
                        chunk_count,
                        point_ids,
                        last_error
                    )
                    VALUES (
                        %(id)s,
                        %(bucket)s,
                        %(object_key)s,
                        %(filename)s,
                        %(logical_filename)s,
                        %(document_version)s,
                        %(tags)s,
                        %(lexical_hash)s,
                        %(status)s,
                        %(etag)s,
                        %(size)s,
                        %(last_modified)s,
                        COALESCE(%(last_seen_at)s, NOW()),
                        %(indexed_at)s,
                        %(chunk_count)s,
                        %(point_ids)s,
                        %(last_error)s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {
                        "id": doc_id,
                        "bucket": bucket,
                        "object_key": key,
                        "filename": record.get("filename") or PurePosixPath(key).name,
                        "logical_filename": record.get("logical_filename")
                        or record.get("filename")
                        or PurePosixPath(key).name,
                        "document_version": record.get("document_version"),
                        "tags": Jsonb(record.get("tags") or []),
                        "lexical_hash": record.get("lexical_hash"),
                        "status": record.get("status") or NOT_INDEXED,
                        "etag": record.get("etag"),
                        "size": record.get("size"),
                        "last_modified": record.get("last_modified"),
                        "last_seen_at": record.get("last_seen_at"),
                        "indexed_at": record.get("indexed_at"),
                        "chunk_count": record.get("chunk_count") or 0,
                        "point_ids": Jsonb(record.get("point_ids") or []),
                        "last_error": record.get("last_error"),
                    },
                )
                migrated += cursor.rowcount

        conn.commit()

    logger.info("legacy document registry migration completed", extra={"event": {"migrated": migrated}})
    trace(f"Legacy document registry migration completed with {migrated} record(s)", logger)
    return migrated
