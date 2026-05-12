"""
API router module.

This module defines the main API router that aggregates all endpoint routes.
It serves as the central routing configuration for the FastAPI application,
organizing routes by domain (users, journals, knowledge, etc.).
"""

from fastapi import APIRouter

# Create the main API router
api_router = APIRouter()

# TODO: Include sub-routers for different domains
# Example:
# from app.api.users import router as users_router
# from app.api.journals import router as journals_router
# from app.api.knowledge import router as knowledge_router

# Include versioned API routers
from app.api.v1.router import api_v1_router
api_router.include_router(api_v1_router)

# TODO: Add API versioning strategy
# TODO: Add middleware for API versioning
# TODO: Add rate limiting and authentication