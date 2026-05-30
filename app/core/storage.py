from __future__ import annotations

from typing import Any

from app.core.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PREFIX,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
    S3_USE_SSL,
    S3_VERIFY_SSL,
)
from app.core.logging import get_logger, log_timing

logger = get_logger(__name__)

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".ppt": "ppt",
    ".pptx": "pptx",
    ".txt": "text",
    ".md": "text",
}

DOCUMENT_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def s3_client():
    import boto3
    from botocore.config import Config

    logger.debug(
        "s3 client creating",
        extra={"event": {"endpoint": S3_ENDPOINT_URL, "bucket": S3_BUCKET}},
    )
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        region_name=S3_REGION_NAME,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        use_ssl=S3_USE_SSL,
        verify=S3_VERIFY_SSL,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(client: Any | None = None, *, bucket: str = S3_BUCKET) -> None:
    client = client or s3_client()
    try:
        client.head_bucket(Bucket=bucket)
        logger.debug("s3 bucket exists", extra={"event": {"bucket": bucket}})
        return
    except Exception as exc:
        response = getattr(exc, "response", {}) or {}
        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        error_code = response.get("Error", {}).get("Code")
        if status_code not in {404, 400} and error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    create_kwargs = {"Bucket": bucket}
    if S3_REGION_NAME and S3_REGION_NAME != "us-east-1" and not S3_ENDPOINT_URL:
        create_kwargs["CreateBucketConfiguration"] = {
            "LocationConstraint": S3_REGION_NAME
        }

    logger.info("s3 bucket creating", extra={"event": {"bucket": bucket}})
    client.create_bucket(**create_kwargs)


def document_extension(filename: str) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"Unsupported document type {suffix or '<none>'}. Supported types: {allowed}.")

    return suffix


def document_file_type(filename: str) -> str:
    return SUPPORTED_DOCUMENT_EXTENSIONS[document_extension(filename)]


def document_content_type(filename: str, fallback: str | None = None) -> str:
    return DOCUMENT_CONTENT_TYPES.get(document_extension(filename), fallback or "application/octet-stream")


def is_supported_document_key(key: str) -> bool:
    suffix = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return suffix in SUPPORTED_DOCUMENT_EXTENSIONS


def list_document_objects(
    client: Any | None = None,
    *,
    bucket: str = S3_BUCKET,
    prefix: str = S3_PREFIX,
) -> list[dict]:
    client = client or s3_client()
    ensure_bucket(client, bucket=bucket)
    paginator = client.get_paginator("list_objects_v2")
    objects = []

    with log_timing(logger, "s3_list_document_objects", bucket=bucket, prefix=prefix):
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if is_supported_document_key(key):
                    objects.append(item)

    logger.info(
        "s3 document objects listed",
        extra={"event": {"bucket": bucket, "prefix": prefix, "object_count": len(objects)}},
    )
    return objects


def list_pdf_objects(*args, **kwargs) -> list[dict]:
    """Backward-compatible wrapper; now lists all supported document objects."""
    return list_document_objects(*args, **kwargs)


def s3_item_from_head(key: str, head: dict) -> dict:
    return {
        "Key": key,
        "ETag": head.get("ETag"),
        "Size": head.get("ContentLength"),
        "LastModified": head.get("LastModified"),
    }
