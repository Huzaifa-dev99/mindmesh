"""
API router module.

This module defines the main API router that aggregates all endpoint routes.
It serves as the central routing configuration for the FastAPI application,
organizing routes by domain (users, journals, knowledge, etc.).
"""

from fastapi import APIRouter

api_router = APIRouter()

from app.api.v1.router import api_v1_router

api_router.include_router(api_v1_router)
