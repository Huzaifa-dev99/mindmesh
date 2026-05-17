import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MinioObjectPath:
    bucket: str
    object_name: str


def split_minio_object_path(object_path: str) -> MinioObjectPath:
    normalized = object_path.replace("\\", "/").strip("/")
    bucket_prefix = f"{settings.MINIO_BUCKET}/"
    if normalized == settings.MINIO_BUCKET:
        return MinioObjectPath(settings.MINIO_BUCKET, "")
    if normalized.startswith(bucket_prefix):
        return MinioObjectPath(settings.MINIO_BUCKET, normalized[len(bucket_prefix):])
    return MinioObjectPath(settings.MINIO_BUCKET, normalized)


class LocalDocumentStorage:
    def __init__(self, base_path: str | Path | None = None) -> None:
        self.base_path = Path(base_path or settings.MINIO_DATA_PATH)

    def save_bytes(self, object_path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        target = self.base_path / object_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def delete(self, object_path: str) -> None:
        target = self.base_path / object_path
        if target.exists():
            target.unlink()


class MinioDocumentStorage:
    def __init__(self, client=None) -> None:
        self.client = client or build_minio_client()

    def save_bytes(self, object_path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        target = split_minio_object_path(object_path)
        if not target.object_name:
            raise ValueError("MinIO object path must include an object name")
        self._ensure_bucket(target.bucket)
        self.client.put_object(
            target.bucket,
            target.object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def delete(self, object_path: str) -> None:
        target = split_minio_object_path(object_path)
        if target.object_name:
            self.client.remove_object(target.bucket, target.object_name)

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)


class PreferMinioDocumentStorage:
    def __init__(self, minio_storage=None, local_storage=None) -> None:
        self.minio_storage = minio_storage
        self.local_storage = local_storage or LocalDocumentStorage()

    def save_bytes(self, object_path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        minio_storage = self._minio_storage()
        if minio_storage is not None:
            try:
                minio_storage.save_bytes(object_path, data, content_type)
                return
            except Exception:
                logger.warning("minio_document_save_failed falling_back_to_local path=%s", object_path, exc_info=True)
        self.local_storage.save_bytes(object_path, data, content_type)

    def delete(self, object_path: str) -> None:
        minio_storage = self._minio_storage()
        if minio_storage is not None:
            try:
                minio_storage.delete(object_path)
            except Exception:
                logger.warning("minio_document_delete_failed path=%s", object_path, exc_info=True)
        self.local_storage.delete(object_path)

    def _minio_storage(self):
        if self.minio_storage is not None:
            return self.minio_storage
        try:
            self.minio_storage = MinioDocumentStorage()
        except Exception:
            logger.warning("minio_client_init_failed falling_back_to_local", exc_info=True)
            self.minio_storage = False
        return self.minio_storage or None


def build_minio_client():
    from minio import Minio

    endpoint = normalize_minio_endpoint(settings.MINIO_ENDPOINT)
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def normalize_minio_endpoint(endpoint: str) -> str:
    if endpoint.startswith(("http://", "https://")):
        parsed = urlparse(endpoint)
        return parsed.netloc
    return endpoint


def create_document_storage() -> PreferMinioDocumentStorage:
    return PreferMinioDocumentStorage()


def check_minio_connection() -> bool:
    try:
        client = build_minio_client()
        client.bucket_exists(settings.MINIO_BUCKET)
        return True
    except Exception:
        logger.exception("minio_health_check_failed")
        return False
