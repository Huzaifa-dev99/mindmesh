"""
Core configuration module.

This module handles all application configuration using Pydantic settings.
It loads environment variables and provides centralized configuration management
for database connections, API keys, and other settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class defines all configurable parameters for the application,
    with sensible defaults where appropriate.
    """

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env", ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "MindMesh Backend"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/v1"
    LOG_LEVEL: str = "INFO"

    # Database configuration
    POSTGRES_DB: str = "mindmesh"
    POSTGRES_USER: str = "mindmesh_user"
    POSTGRES_PASSWORD: str = "mindmesh_password"
    DATABASE_URL: str = "postgresql://mindmesh_user:mindmesh_password@localhost:5432/mindmesh"

    # AI provider configuration
    GROQ_API_KEY: str = ""

    # Vector database configuration
    QDRANT_URL: str = "http://localhost:6335"
    QDRANT_COLLECTION: str = "mindmesh_memories"
    QDRANT_NOTES_COLLECTION: str = "notes"
    QDRANT_DOCUMENTS_COLLECTION: str = "documents"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384

    # Optional tools and object storage
    TAVILY_API_KEY: str = ""
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = Field("minioadmin", validation_alias=AliasChoices("MINIO_ACCESS_KEY", "MINIO_USER"))
    MINIO_SECRET_KEY: str = Field("minioadmin", validation_alias=AliasChoices("MINIO_SECRET_KEY", "MINIO_PASSWORD"))
    MINIO_BUCKET: str = "mindmesh-documents"
    MINIO_SECURE: bool = False
    MINIO_DATA_PATH: str = ".mindmesh-data/minio"

    # Application settings
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501,http://frontend:8501"

    # Service configuration
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
