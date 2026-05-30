import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def get_optional_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value == "":
        return None

    return value


def get_int_env(name: str, default: int | None = None) -> int:
    value = get_env(name, None if default is None else str(default))
    return int(value)


def get_float_env(name: str, default: float | None = None) -> float:
    value = get_env(name, None if default is None else str(default))
    return float(value)


def get_bool_env(name: str, default: bool = False) -> bool:
    value = get_optional_env(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def get_list_env(name: str) -> list[str]:
    value = get_optional_env(name)
    if value is None:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def get_path_env(name: str, default: str) -> Path:
    value = get_optional_env(name, default)
    path = Path(value or default)
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


APP_NAME = get_env("APP_NAME", "MM POC RAG API")
API_V1_PREFIX = get_env("API_V1_PREFIX", "/api/v1")
ADMIN_SECRET_KEY = get_optional_env("ADMIN_SECRET_KEY")

DATABASE_URL = get_optional_env("DATABASE_URL")
POSTGRES_HOST = get_env("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = get_int_env("POSTGRES_PORT", default=5432)
POSTGRES_DB = get_env("POSTGRES_DB", "mm_poc")
POSTGRES_USER = get_env("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = get_optional_env("POSTGRES_PASSWORD")
POSTGRES_SSLMODE = get_optional_env("POSTGRES_SSLMODE", "disable")
POSTGRES_CONNECT_TIMEOUT = get_int_env("POSTGRES_CONNECT_TIMEOUT", default=5)

S3_ENDPOINT_URL = get_env("S3_ENDPOINT_URL")
S3_BUCKET = get_env("S3_BUCKET")
S3_PREFIX = get_env("S3_PREFIX")
S3_REGION_NAME = get_optional_env("S3_REGION_NAME")
S3_ACCESS_KEY_ID = get_optional_env("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = get_optional_env("S3_SECRET_ACCESS_KEY")
S3_USE_SSL = get_bool_env("S3_USE_SSL", default=True)
S3_VERIFY_SSL = get_bool_env("S3_VERIFY_SSL", default=True)

CHUNK_SIZE = get_int_env("CHUNK_SIZE")
CHUNK_OVERLAP = get_int_env("CHUNK_OVERLAP")
RETRIEVER_TOP_K = get_int_env("RETRIEVER_TOP_K", default=4)
RETRIEVER_SCORE_THRESHOLD = get_float_env("RETRIEVER_SCORE_THRESHOLD", default=0.0)

TAVILY_API_KEY = get_optional_env("TAVILY_API_KEY")
TAVILY_SEARCH_DEPTH = get_env("TAVILY_SEARCH_DEPTH", "basic")
TAVILY_MAX_RESULTS = get_int_env("TAVILY_MAX_RESULTS", default=5)
TAVILY_INCLUDE_ANSWER = get_bool_env("TAVILY_INCLUDE_ANSWER", default=True)
TAVILY_INCLUDE_RAW_CONTENT = get_bool_env(
    "TAVILY_INCLUDE_RAW_CONTENT",
    default=False,
)

QDRANT_URL = get_env("QDRANT_URL")
QDRANT_COLLECTION_NAME = get_env("QDRANT_COLLECTION_NAME")
QDRANT_DISTANCE = get_env("QDRANT_DISTANCE")
QDRANT_RECREATE_COLLECTION = get_bool_env("QDRANT_RECREATE_COLLECTION", default=False)

EMBEDDING_MODEL_NAME = get_env("EMBEDDING_MODEL_NAME")
EMBEDDING_DIMENSION = get_int_env("EMBEDDING_DIMENSION")
EMBEDDING_MODEL_PATH = (
    PROJECT_ROOT / "models" / "embedding" / EMBEDDING_MODEL_NAME.replace("/", "__")
)

CONTENT_PAYLOAD_KEY = get_env("CONTENT_PAYLOAD_KEY")
METADATA_PAYLOAD_KEY = get_env("METADATA_PAYLOAD_KEY")

DOCUMENT_TAGS = get_list_env("DOCUMENT_TAGS")
DOCUMENT_APPLICABLE_DATA = get_optional_env("DOCUMENT_APPLICABLE_DATA")
DOCUMENT_VERSION = get_optional_env("DOCUMENT_VERSION")
DOCUMENT_REGISTRY_PATH = get_path_env(
    "DOCUMENT_REGISTRY_PATH",
    "document_registry.json",
)

GROQ_API_KEY = get_optional_env("GROQ_API_KEY")
GROQ_MODEL = get_env("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MAX_TOKENS = get_int_env("GROQ_MAX_TOKENS", default=1024)
GROQ_TEMPERATURE = get_float_env("GROQ_TEMPERATURE", default=0.0)
