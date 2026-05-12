"""
Main FastAPI application module.

This module initializes the FastAPI application instance and configures
the core settings, middleware, and routing for the MindMesh backend API.
"""

from fastapi import FastAPI

from app.core.config import settings
from app.api.router import api_router

# Create the FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered journaling and knowledge management platform",
)

# Include API routers
app.include_router(api_router)

# TODO: Add middleware (CORS, authentication, etc.)
# TODO: Add database initialization
# TODO: Add startup/shutdown event handlers

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}