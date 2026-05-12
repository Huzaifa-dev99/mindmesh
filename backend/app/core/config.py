"""
Core configuration module.

This module handles all application configuration using Pydantic settings.
It loads environment variables and provides centralized configuration management
for database connections, API keys, and other settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class defines all configurable parameters for the application,
    with sensible defaults where appropriate.
    """

    # Project metadata
    PROJECT_NAME: str = "MindMesh Backend"
    VERSION: str = "0.1.0"

    # Database configuration
    POSTGRES_DB: str = "mindmesh"
    POSTGRES_USER: str = "mindmesh_user"
    POSTGRES_PASSWORD: str = "mindmesh_password"
    DATABASE_URL: str = "postgresql://mindmesh_user:mindmesh_password@localhost:5432/mindmesh"

    # AI provider configuration
    GROQ_API_KEY: str = ""

    # Vector database configuration
    QDRANT_URL: str = "http://localhost:6333"

    # Application settings
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here"

    # Service configuration
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()