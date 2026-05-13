"""
Main FastAPI application module.

This module initializes the FastAPI application instance and configures
the core settings, middleware, and routing for the MindMesh backend API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.qdrant import ensure_agent_collections, ensure_collection

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("mindmesh_backend_starting env=%s version=%s", settings.APP_ENV, settings.VERSION)
    try:
        ensure_collection()
        ensure_agent_collections()
    except Exception:
        logger.exception("qdrant_collection_init_failed")
    yield
    logger.info("mindmesh_backend_stopping")

# Create the FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered journaling and knowledge management platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

# Include API routers
app.include_router(api_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}
