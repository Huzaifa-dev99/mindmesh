import re
from datetime import datetime, timedelta, timezone
from tempfile import NamedTemporaryFile
from pathlib import PurePosixPath
from typing import Any

from langchain_community.document_loaders.base import BaseLoader

from app.core.config import (
    DOCUMENT_APPLICABLE_DATA,
    DOCUMENT_TAGS,
    DOCUMENT_VERSION,
    S3_BUCKET,
)
from app.core.logging import get_logger, log_timing, trace
from app.core.storage import document_file_type, list_document_objects, s3_client
from app.services.document_registry import INDEXED, sync_documents

logger = get_logger(__name__)

METADATA_KEYS = (
    "filename",
    "author",
    "created_at",
    "indexed_at",
    "tags",
    "document_applicable_data",
    "document_version",
    "document_id",
    "page_number",
    "file_type",
)
REGISTRY_ID_METADATA_KEY = "_registry_id"
DOCLING_EXTENSIONS = {".pdf", ".docx", ".ppt", ".pptx"}
TEXT_EXTENSIONS = {".txt", ".md"}


class S3DocumentLoader(BaseLoader):
    """Load supported documents from S3/MinIO and parse them for indexing."""

    def __init__(self, document_ids: list[str] | None = None):
        self.document_ids = set(document_ids or [])

    def load(self):
        from langchain_core.documents import Document

        trace("S3 document loading started", logger)
        client = s3_client()
        indexed_at = datetime.now(timezone.utc).isoformat()
        docs = []

        s3_objects = list_document_objects(client)
        records = sync_documents(s3_objects)

        for record in records:
            if self.document_ids and record["id"] not in self.document_ids:
                continue
            if record.get("status") == INDEXED:
                continue

            key = record["key"]
            file_type = document_file_type(key)
            logger.info("s3 document object loading", extra={"event": {"document_id": record["id"], "key": key, "file_type": file_type}})
            response = client.get_object(Bucket=S3_BUCKET, Key=key)
            s3_metadata = response.get("Metadata") or {}
            last_modified = response.get("LastModified")
            body = response["Body"].read()
            extension = PurePosixPath(key).suffix.lower()

            if extension in DOCLING_EXTENSIONS:
                parsed_documents = _load_with_docling(body, key)
            elif extension in TEXT_EXTENSIONS:
                parsed_documents = [
                    Document(
                        page_content=body.decode("utf-8", errors="ignore"),
                        metadata={},
                    )
                ]
            else:
                logger.warning("unsupported document skipped during loading", extra={"event": {"key": key}})
                continue

            for document in parsed_documents:
                raw_metadata = dict(document.metadata or {})
                document.metadata = _fixed_metadata(
                    raw_metadata=raw_metadata,
                    s3_key=key,
                    s3_metadata=s3_metadata,
                    last_modified=last_modified,
                    indexed_at=indexed_at,
                    document_id=record["id"],
                    page_number=_page_number(raw_metadata),
                    file_type=file_type,
                )
                document.metadata[REGISTRY_ID_METADATA_KEY] = record["id"]
                docs.append(document)

        logger.info(
            "s3 document loading completed",
            extra={"event": {"object_count": len(s3_objects), "document_count": len(docs)}},
        )
        trace(f"S3 document loading completed with {len(docs)} parsed chunk(s)", logger)
        return docs


S3PyPDFLoader = S3DocumentLoader


def _load_with_docling(content: bytes, key: str):
    from langchain_docling import DoclingLoader
    from langchain_docling.loader import ExportType

    suffix = PurePosixPath(key).suffix.lower()
    with NamedTemporaryFile(suffix=suffix, delete=False) as file:
        file.write(content)
        file_path = file.name

    try:
        loader = DoclingLoader(file_path=file_path, export_type=ExportType.DOC_CHUNKS)
        return loader.load()
    finally:
        try:
            import os

            os.unlink(file_path)
        except OSError:
            logger.warning("temporary docling file cleanup failed", extra={"event": {"path": file_path}}, exc_info=True)


def _split_tags(value: str | None) -> list[str]:
    if not value:
        return []

    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _metadata_value(metadata: dict, *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value

    return None


def _iso_datetime(value: Any) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    text = str(value).strip()
    match = re.match(
        r"^D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz]|[+-]\d{2}'?\d{2}'?)?",
        text,
    )
    if not match:
        return text

    year, month, day, hour, minute, second, offset = match.groups()
    tzinfo = timezone.utc

    if offset and offset.upper() != "Z":
        sign = 1 if offset.startswith("+") else -1
        digits = re.sub(r"\D", "", offset)
        offset_hours = int(digits[:2] or 0)
        offset_minutes = int(digits[2:4] or 0)
        tzinfo = timezone(sign * timedelta(hours=offset_hours, minutes=offset_minutes))

    return datetime(
        int(year),
        int(month or 1),
        int(day or 1),
        int(hour or 0),
        int(minute or 0),
        int(second or 0),
        tzinfo=tzinfo,
    ).isoformat()


def _page_number(metadata: dict) -> int | None:
    for key in ("page_number", "page_no", "page"):
        value = metadata.get(key)
        if value not in (None, ""):
            try:
                return int(value)
            except (TypeError, ValueError):
                pass

    dl_meta = metadata.get("dl_meta")
    if not isinstance(dl_meta, dict):
        return None

    pages = []
    for item in dl_meta.get("doc_items") or []:
        if not isinstance(item, dict):
            continue
        for provenance in item.get("prov") or []:
            if isinstance(provenance, dict) and provenance.get("page_no") is not None:
                try:
                    pages.append(int(provenance["page_no"]))
                except (TypeError, ValueError):
                    pass

    return min(pages) if pages else None


def _fixed_metadata(
    raw_metadata: dict,
    s3_key: str,
    s3_metadata: dict,
    last_modified: datetime | None,
    indexed_at: str,
    document_id: str | None = None,
    page_number: int | None = None,
    file_type: str | None = None,
) -> dict:
    filename = _metadata_value(s3_metadata, "filename") or PurePosixPath(s3_key).name
    tags = DOCUMENT_TAGS + _split_tags(_metadata_value(s3_metadata, "tags"))

    metadata = {
        "filename": filename,
        "author": _metadata_value(raw_metadata, "author")
        or _metadata_value(s3_metadata, "author")
        or "",
        "created_at": (
            _iso_datetime(_metadata_value(raw_metadata, "creationdate", "created_at"))
            or _iso_datetime(_metadata_value(s3_metadata, "created_at", "created-at"))
            or _iso_datetime(last_modified)
        ),
        "indexed_at": indexed_at,
        "tags": tags,
        "document_applicable_data": (
            _metadata_value(
                s3_metadata,
                "document_applicable_data",
                "document-applicable-data",
            )
            or DOCUMENT_APPLICABLE_DATA
        ),
        "document_version": (
            _metadata_value(s3_metadata, "document_version", "document-version")
            or DOCUMENT_VERSION
        ),
        "document_id": document_id,
        "page_number": page_number,
        "file_type": file_type or document_file_type(filename),
    }

    return {key: metadata.get(key) for key in METADATA_KEYS}


def load_s3_pdf_docs(document_ids: list[str] | None = None):
    return S3DocumentLoader(document_ids=document_ids).load()


def load_s3_documents(document_ids: list[str] | None = None):
    return S3DocumentLoader(document_ids=document_ids).load()


def chunk_docs(docs, chunk_size: int, chunk_overlap: int):
    """Split documents into chunks while preserving the fixed metadata schema."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    trace(f"Document chunking started for {len(docs)} document page(s)", logger)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    with log_timing(logger, "document_chunking", document_count=len(docs), chunk_size=chunk_size):
        chunks = text_splitter.split_documents(docs)
    for chunk in chunks:
        chunk.metadata = {
            key: chunk.metadata.get(key)
            for key in (*METADATA_KEYS, REGISTRY_ID_METADATA_KEY)
        }

    logger.info("document chunking completed", extra={"event": {"chunk_count": len(chunks)}})
    trace(f"Document chunking completed with {len(chunks)} chunk(s)", logger)
    return chunks


def load_docs(
    chunk_size: int,
    chunk_overlap: int,
    document_ids: list[str] | None = None,
):
    """Load S3 documents, parse them, and return recursively chunked documents."""
    trace("Document preprocessing started", logger)
    with log_timing(logger, "document_preprocessing", document_filter_count=len(document_ids or [])):
        docs = load_s3_pdf_docs(document_ids=document_ids)
        chunks = chunk_docs(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    trace("Document preprocessing completed", logger)
    return chunks
