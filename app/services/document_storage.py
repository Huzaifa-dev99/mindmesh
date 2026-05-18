from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

from pypdf import PdfReader

from app.core.config import S3_BUCKET, S3_PREFIX
from app.core.logging import get_logger, log_timing, trace
from app.core.storage import (
    document_content_type,
    document_extension,
    document_file_type,
    list_document_objects,
    s3_client,
    s3_item_from_head,
)
from app.services.document_registry import (
    delete_documents,
    document_id,
    find_document_by_lexical_hash,
    find_document_versions,
    get_documents,
    register_uploaded_document,
    sync_documents,
)

logger = get_logger(__name__)


@dataclass
class UploadCandidate:
    original_filename: str
    content: bytes
    content_type: str | None
    filename: str
    tags: list[str]


@dataclass
class UploadResult:
    documents: list[dict]
    skipped: list[dict]


def _safe_document_filename(filename: str) -> str:
    base_name = PurePosixPath(filename.strip()).name
    if not base_name:
        raise ValueError("Filename cannot be empty")

    extension = document_extension(base_name)
    stem = PurePosixPath(base_name).stem
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "", stem).strip(" ._")
    if not stem:
        raise ValueError(f"Filename is not valid: {filename}")

    return f"{stem}{extension}"


def _filename_with_original_extension(filename: str, original_filename: str) -> str:
    if PurePosixPath(filename).suffix:
        return filename

    original_extension = PurePosixPath(original_filename).suffix
    return f"{filename}{original_extension}" if original_extension else filename


def _safe_pdf_filename(filename: str) -> str:
    """Backward-compatible wrapper for older tests/imports."""
    return _safe_document_filename(filename)


def _versioned_key(filename: str, version: str) -> str:
    stem = PurePosixPath(filename).stem
    extension = PurePosixPath(filename).suffix.lower()
    versioned_filename = f"{stem}_v{version}{extension}"
    prefix = S3_PREFIX.strip("/")
    if not prefix:
        return versioned_filename

    return f"{prefix}/{versioned_filename}"


def _extract_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _lexical_hash(content: bytes, filename: str | None = None) -> str:
    logger.debug("lexical hash calculation started", extra={"event": {"size_bytes": len(content)}})
    suffix = PurePosixPath(filename or "").suffix.lower()
    if suffix in {".txt", ".md"}:
        text = content.decode("utf-8", errors="ignore")
        normalized_text = " ".join(text.lower().split())
        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    if suffix and suffix != ".pdf":
        return hashlib.sha256(content).hexdigest()

    try:
        text = _extract_text(content)
    except Exception:
        logger.exception("pdf text extraction failed during lexical hash")
        text = ""

    normalized = " ".join(text.lower().split())
    if not normalized:
        return hashlib.sha256(content).hexdigest()

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _next_version(previous_versions: list[dict]) -> str:
    numbers = []
    for document in previous_versions:
        value = document.get("document_version")
        if value and str(value).isdigit():
            numbers.append(int(value))

    next_number = max(numbers, default=0) + 1
    return f"{next_number:02d}"


def parse_tags(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        candidates = value.split(",")
    else:
        candidates = value

    return list(dict.fromkeys(tag.strip() for tag in candidates if tag.strip()))


def sync_storage_documents() -> list[dict]:
    trace("S3 document sync started", logger)
    objects = list_document_objects(bucket=S3_BUCKET, prefix=S3_PREFIX)
    documents = sync_documents(objects)
    logger.info("s3 document sync completed", extra={"event": {"object_count": len(objects), "document_count": len(documents)}})
    trace(f"S3 document sync completed with {len(documents)} document(s)", logger)
    return documents


def upload_documents(candidates: list[UploadCandidate]) -> UploadResult:
    trace(f"Document upload started for {len(candidates)} candidate(s)", logger)
    client = s3_client()
    uploaded = []
    skipped = []

    with log_timing(logger, "upload_documents", candidate_count=len(candidates)):
        for candidate in candidates:
            filename = _safe_document_filename(
                _filename_with_original_extension(candidate.filename, candidate.original_filename)
            )
            logical_filename = filename.lower()
            file_type = document_file_type(filename)
            lexical_hash = _lexical_hash(candidate.content, filename)
            previous_versions = find_document_versions(S3_BUCKET, logical_filename)
            duplicate = find_document_by_lexical_hash(S3_BUCKET, lexical_hash)

            if duplicate:
                logger.info(
                    "document upload skipped duplicate",
                    extra={"event": {"filename": filename, "existing_document_id": duplicate["id"]}},
                )
                skipped.append(
                    {
                        "filename": filename,
                        "tags": candidate.tags,
                        "reason": "Document already exists with identical lexical content.",
                        "existing_document_id": duplicate["id"],
                        "existing_filename": duplicate.get("filename"),
                        "existing_key": duplicate.get("key"),
                        "existing_version": duplicate.get("document_version"),
                    }
                )
                continue

            version = _next_version(previous_versions)
            key = _versioned_key(filename, version)
            tags = parse_tags(candidate.tags)
            logger.info("document upload putting object", extra={"event": {"filename": filename, "key": key, "size_bytes": len(candidate.content)}})
            client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=candidate.content,
                ContentType=candidate.content_type or document_content_type(filename),
                Metadata={
                    "filename": filename,
                    "logical-filename": logical_filename,
                    "document-version": version,
                    "tags": ",".join(tags),
                    "lexical-hash": lexical_hash,
                    "file-type": file_type,
                },
            )
            head = client.head_object(Bucket=S3_BUCKET, Key=key)
            item = s3_item_from_head(key, head)
            document = register_uploaded_document(
                doc_id=document_id(S3_BUCKET, key),
                bucket=S3_BUCKET,
                key=key,
                filename=filename,
                logical_filename=logical_filename,
                document_version=version,
                tags=tags,
                lexical_hash=lexical_hash,
                etag=str(item.get("ETag") or "").strip('"'),
                size=item.get("Size"),
                last_modified=item.get("LastModified"),
            )
            uploaded.append(document)

    trace(f"Document upload completed with {len(uploaded)} uploaded and {len(skipped)} skipped", logger)
    return UploadResult(documents=uploaded, skipped=skipped)


def remove_documents_from_storage(document_ids: list[str]) -> int:
    trace(f"Storage removal started for {len(document_ids)} document(s)", logger)
    documents = get_documents(document_ids)
    if not documents:
        logger.info("storage removal skipped without matching documents")
        return 0

    client = s3_client()
    objects = [{"Key": document["key"]} for document in documents if document.get("key")]
    if objects:
        with log_timing(logger, "s3_delete_documents", object_count=len(objects)):
            client.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objects})

    removed = delete_documents([document["id"] for document in documents])
    trace(f"Storage removal completed with {removed} document(s) removed", logger)
    return removed
