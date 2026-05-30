from collections import defaultdict
from dataclasses import dataclass, field

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE, S3_BUCKET, S3_PREFIX
from app.core.logging import get_logger, log_timing, trace
from app.services.document_registry import (
    INDEXED,
    is_indexed,
    list_documents,
    mark_indexed,
    mark_not_indexed,
)
from app.services.preprocessing import METADATA_KEYS, REGISTRY_ID_METADATA_KEY, load_docs

logger = get_logger(__name__)


@dataclass
class IndexedDocument:
    id: str
    filename: str
    status: str
    chunk_count: int = 0
    point_ids: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class IndexResult:
    source: str
    indexed_documents: int
    indexed_chunks: int
    skipped_documents: int
    documents: list[IndexedDocument] = field(default_factory=list)


def _raw_metadata(document) -> dict:
    return dict(getattr(document, "metadata", {}) or {})


def _qdrant_metadata(document) -> dict:
    metadata = _raw_metadata(document)
    return {key: metadata.get(key) for key in METADATA_KEYS}


def _registry_id(document) -> str:
    registry_id = _raw_metadata(document).get(REGISTRY_ID_METADATA_KEY)
    if not registry_id:
        raise ValueError("Document is missing registry id metadata")

    return registry_id


def _filename(chunks: list) -> str:
    return _qdrant_metadata(chunks[0]).get("filename") or "document"


def _chunks_by_document(chunks: list) -> dict[str, list]:
    grouped = defaultdict(list)
    for chunk in chunks:
        grouped[_registry_id(chunk)].append(chunk)

    return dict(grouped)


def _source_label() -> str:
    return f"s3://{S3_BUCKET}/{S3_PREFIX}"


def _print(message: str, enabled: bool) -> None:
    if enabled:
        trace(message, logger)


def index_documents(
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    show_progress: bool = True,
    document_ids: list[str] | None = None,
) -> IndexResult:
    trace("Indexing job started", logger)
    logger.info(
        "indexing job started",
        extra={
            "event": {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "document_count_requested": len(document_ids or []),
            }
        },
    )
    _print(f"Loading unindexed documents from {_source_label()}", show_progress)
    with log_timing(logger, "load_documents_for_indexing", source=_source_label()):
        chunks = load_docs(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            document_ids=document_ids,
        )
    grouped_chunks = _chunks_by_document(chunks)

    total_documents = len(grouped_chunks)
    total_chunks = len(chunks)
    requested_ids = set(document_ids or [])
    skipped_documents = len(
        [
            document
            for document in list_documents()
            if document.get("status") == INDEXED
            and document.get("bucket") == S3_BUCKET
            and str(document.get("key", "")).startswith(S3_PREFIX)
            and (not requested_ids or document.get("id") in requested_ids)
        ]
    )

    _print(
        f"Loaded {total_chunks} chunk(s) from {total_documents} unindexed document(s)",
        show_progress,
    )

    result = IndexResult(
        source=_source_label(),
        indexed_documents=0,
        indexed_chunks=0,
        skipped_documents=skipped_documents,
    )

    if total_chunks == 0:
        _print("No new documents to index.", show_progress)
        logger.info(
            "indexing job completed without new chunks",
            extra={"event": {"skipped_documents": skipped_documents}},
        )
        trace("Indexing job completed", logger)
        return result

    from app.core.clients import get_qdrant_vector_store

    qdrant_vs = get_qdrant_vector_store()
    with log_timing(logger, "index_documents_to_qdrant", total_documents=total_documents, total_chunks=total_chunks):
        for current, (doc_id, document_chunks) in enumerate(grouped_chunks.items(), start=1):
            filename = _filename(document_chunks)
            if is_indexed(doc_id):
                logger.info(
                    "document already indexed",
                    extra={"event": {"document_id": doc_id, "filename": filename}},
                )
                _print(f"Skipping [{current}/{total_documents}] {filename}", show_progress)
                continue

            document_ids = []
            _print(
                f"Indexing [{current}/{total_documents}] {filename} "
                f"({len(document_chunks)} chunk(s))",
                show_progress,
            )

            try:
                inserted_ids = qdrant_vs.add_texts(
                    texts=[chunk.page_content for chunk in document_chunks],
                    metadatas=[_qdrant_metadata(chunk) for chunk in document_chunks],
                )
                document_ids.extend(inserted_ids or [])

                mark_indexed(doc_id, chunk_count=len(document_chunks), point_ids=document_ids)
                result.indexed_documents += 1
                result.indexed_chunks += len(document_chunks)
                logger.info(
                    "document indexed",
                    extra={
                        "event": {
                            "document_id": doc_id,
                            "filename": filename,
                            "chunk_count": len(document_chunks),
                            "point_count": len(document_ids),
                        }
                    },
                )
                result.documents.append(
                    IndexedDocument(
                        id=doc_id,
                        filename=filename,
                        status=INDEXED,
                        chunk_count=len(document_chunks),
                        point_ids=[str(point_id) for point_id in document_ids],
                    )
                )
            except Exception as exc:
                logger.exception(
                    "document indexing failed",
                    extra={"event": {"document_id": doc_id, "filename": filename}},
                )
                trace(f"Indexing failed for {filename}", logger)
                mark_not_indexed(doc_id, error=str(exc))
                result.documents.append(
                    IndexedDocument(
                        id=doc_id,
                        filename=filename,
                        status="failed",
                        chunk_count=len(document_chunks),
                        error=str(exc),
                    )
                )
                raise

    _print(f"Added {result.indexed_chunks} chunk(s) to Qdrant", show_progress)
    logger.info(
        "indexing job completed",
        extra={
            "event": {
                "indexed_documents": result.indexed_documents,
                "indexed_chunks": result.indexed_chunks,
                "skipped_documents": result.skipped_documents,
            }
        },
    )
    trace("Indexing job completed", logger)
    return result
