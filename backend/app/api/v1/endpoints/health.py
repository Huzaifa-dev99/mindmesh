"""
Health check endpoints.

This module provides basic health check functionality for monitoring
the API status and dependencies.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.db.qdrant import check_qdrant_connection
from app.db.session import check_db_connection

router = APIRouter()

@router.get("/")
async def health_check():
    """Basic API health check."""
    return {"status": "healthy", "version": settings.VERSION}

@router.get("/db")
async def database_health_check():
    """Database connectivity health check."""
    healthy = await check_db_connection()
    return {"status": "healthy" if healthy else "unhealthy", "database": healthy}

@router.get("/full")
async def full_health_check():
    """Comprehensive health check including all dependencies."""
    database = await check_db_connection()
    qdrant = check_qdrant_connection()
    return {
        "status": "healthy" if database and qdrant else "degraded",
        "version": settings.VERSION,
        "checks": {
            "database": database,
            "qdrant": qdrant,
            "groq_api_configured": bool(settings.GROQ_API_KEY),
        }
    }
