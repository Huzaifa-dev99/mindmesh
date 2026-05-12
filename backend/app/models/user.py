"""
Database models module.

This module defines SQLAlchemy ORM models that represent database tables.
Models encapsulate the data structure and relationships in the database.

Model Responsibilities:
- Define database table schemas with SQLAlchemy
- Establish relationships between entities
- Provide data validation at the database level
- Support database migrations through Alembic
- Include indexes and constraints for performance and data integrity

Architecture Notes:
- Uses SQLAlchemy declarative base from db.base
- Follows naming conventions for table and column names
- Includes proper typing for all fields
- Supports soft deletes where appropriate
- Ready for multi-tenant architecture if needed
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """
    User model representing application users.

    This model stores user account information and authentication details.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    journals = relationship("Journal", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Journal(Base):
    """
    Journal entry model.

    This model stores individual journal entries with content, metadata, and AI insights.
    """
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    content = Column(Text, nullable=False)
    mood = Column(String(50))
    tags = Column(String(1000))  # JSON string of tags
    is_private = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="journals")

    def __repr__(self):
        return f"<Journal(id={self.id}, title={self.title})>"


# TODO: Add Knowledge model for knowledge graph nodes
# TODO: Add Relationship model for knowledge connections
# TODO: Add AIInsight model for generated insights
# TODO: Add SearchIndex model for search optimization