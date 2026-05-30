from dataclasses import dataclass, field

from qdrant_client import QdrantClient

from app.core.config import QDRANT_COLLECTION_NAME, QDRANT_URL
from app.core.logging import get_logger, log_timing, trace
from app.services.document_registry import clear_document_vectors, get_documents

logger = get_logger(__name__)


@dataclass
class VectorRemovalResult:
    removed_vectors: int = 0
    documents: list[dict] = field(default_factory=list)


def remove_document_vectors(document_ids: list[str]) -> VectorRemovalResult:
    trace(f"Qdrant vector removal started for {len(document_ids)} document(s)", logger)
    documents = get_documents(document_ids)
    point_ids = [
        point_id
        for document in documents
        for point_id in (document.get("point_ids") or [])
    ]

    if point_ids:
        client = QdrantClient(url=QDRANT_URL)
        with log_timing(logger, "qdrant_vector_delete", point_count=len(point_ids)):
            client.delete(
                collection_name=QDRANT_COLLECTION_NAME,
                points_selector=point_ids,
                wait=True,
            )
    else:
        logger.info("qdrant vector removal skipped without point ids")

    updated_documents = clear_document_vectors(
        [document["id"] for document in documents if document.get("id")]
    )
    result = VectorRemovalResult(
        removed_vectors=len(point_ids),
        documents=updated_documents,
    )
    logger.info(
        "qdrant vector removal completed",
        extra={"event": {"document_count": len(updated_documents), "removed_vectors": result.removed_vectors}},
    )
    trace(f"Qdrant vector removal completed with {result.removed_vectors} vector(s)", logger)
    return result


def remove_documents_everywhere(document_ids: list[str]) -> tuple[int, VectorRemovalResult]:
    from app.services.document_storage import remove_documents_from_storage

    trace(f"Document full removal started for {len(document_ids)} document(s)", logger)
    with log_timing(logger, "remove_documents_everywhere", document_count=len(document_ids)):
        vector_result = remove_document_vectors(document_ids)
        removed_documents = remove_documents_from_storage(document_ids)
    logger.info(
        "document full removal completed",
        extra={"event": {"removed_documents": removed_documents, "removed_vectors": vector_result.removed_vectors}},
    )
    trace("Document full removal completed", logger)
    return removed_documents, vector_result
