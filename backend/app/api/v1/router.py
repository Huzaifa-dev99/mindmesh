"""
API v1 router.

This module defines the version 1 API router and aggregates all v1 endpoints.
It provides a centralized location for v1 API route management and versioning.

API Segmentation Plan:
- /v1/auth: Authentication and authorization endpoints
- /v1/users: User management and profiles
- /v1/journals: Journal entry CRUD operations
- /v1/knowledge: Knowledge graph and AI-powered insights
- /v1/search: Unified search across journals and knowledge
- /v1/analytics: Usage analytics and statistics
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, conversations, health, journals, knowledge, search, users

# Create v1 API router with version prefix
api_v1_router = APIRouter(prefix="/v1")

# Include endpoint routers
api_v1_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(journals.router, prefix="/journals", tags=["journals"])
api_v1_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_v1_router.include_router(search.router, prefix="/search", tags=["search"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
