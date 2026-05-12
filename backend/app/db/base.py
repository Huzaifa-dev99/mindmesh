"""
Database base configuration.

This module defines the SQLAlchemy base class and metadata configuration
for the MindMesh database models. It provides the foundation for all database
tables and relationships.

Architecture decisions:
- Uses SQLAlchemy declarative base for ORM mapping
- Centralized metadata management for migrations
- Prepared for multi-model growth with import-based discovery
"""

from sqlalchemy.orm import declarative_base

# SQLAlchemy declarative base for all models
Base = declarative_base()

# Global metadata object for Alembic migrations
# This will be used by Alembic to track database schema changes
metadata = Base.metadata
from app.models import *  # noqa: F401,F403
