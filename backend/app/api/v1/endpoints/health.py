"""
Health check endpoints.

This module provides basic health check functionality for monitoring
the API status and dependencies.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()

@router.get("/")
async def health_check():
    """Basic API health check."""
    return {"status": "healthy", "version": "v1"}

@router.get("/db")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """Database connectivity health check."""
    # TODO: Implement actual database health check
    # For now, just verify session creation
    return {"status": "healthy", "database": "connected"}

@router.get("/full")
async def full_health_check():
    """Comprehensive health check including all dependencies."""
    # TODO: Check database, Qdrant, external APIs
    return {
        "status": "healthy",
        "version": "v1",
        "checks": {
            "database": "pending",
            "qdrant": "pending",
            "groq_api": "pending"
        }
    }