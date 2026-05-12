"""
Configuration utilities for the frontend application.

This module provides utilities for loading and managing environment
configuration in the Streamlit frontend. It handles environment variables
and provides a centralized way to access configuration settings.
"""

import os
from typing import Optional


class FrontendConfig:
    """
    Frontend configuration class.

    This class loads and provides access to frontend-specific configuration
    settings from environment variables.
    """

    # Backend service configuration
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

    # Frontend service configuration
    FRONTEND_PORT: int = 8501

    # Application settings
    APP_ENV: str = "development"
    DEBUG: bool = False

    def __init__(self):
        """Initialize configuration from environment variables."""
        # TODO: Load from .env file or Streamlit secrets
        # For now, using os.environ with defaults

        self.BACKEND_HOST = os.getenv("BACKEND_HOST", self.BACKEND_HOST)
        self.BACKEND_PORT = int(os.getenv("BACKEND_PORT", self.BACKEND_PORT))
        self.FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", self.FRONTEND_PORT))
        self.APP_ENV = os.getenv("APP_ENV", self.APP_ENV)
        self.DEBUG = os.getenv("DEBUG", str(self.DEBUG)).lower() == "true"

        # Reconstruct backend URL
        self.BACKEND_URL = f"http://{self.BACKEND_HOST}:{self.BACKEND_PORT}"

    def get_backend_url(self, path: str = "") -> str:
        """
        Get the full backend URL for a given path.

        Args:
            path: API endpoint path (e.g., "/api/v1/users")

        Returns:
            Full URL string
        """
        return f"{self.BACKEND_URL}{path}"


# Global configuration instance
config = FrontendConfig()