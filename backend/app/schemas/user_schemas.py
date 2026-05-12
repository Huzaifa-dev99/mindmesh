"""
Pydantic schemas for API data validation and serialization.

This module defines Pydantic models used for request/response validation,
data serialization, and API documentation. Schemas ensure data consistency
between API endpoints and internal business logic.

Schema Responsibilities:
- Validate incoming request data
- Serialize outgoing response data
- Generate OpenAPI documentation automatically
- Transform data between API and internal formats
- Handle optional fields and defaults appropriately

Architecture Notes:
- Uses Pydantic v2 features for performance
- Separates create, update, and response schemas
- Includes proper field validation and constraints
- Supports nested relationships where needed
- Ready for API versioning and evolution
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating new users."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating existing users."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Journal Schemas
class JournalBase(BaseModel):
    """Base journal schema with common fields."""
    title: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    mood: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(default_factory=list)
    is_private: bool = True


class JournalCreate(JournalBase):
    """Schema for creating journal entries."""
    pass


class JournalUpdate(BaseModel):
    """Schema for updating journal entries."""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    mood: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    is_private: Optional[bool] = None


class JournalResponse(JournalBase):
    """Schema for journal responses."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# TODO: Add Knowledge schemas for knowledge graph operations
# TODO: Add Search schemas for search requests/responses
# TODO: Add Analytics schemas for reporting data
# TODO: Add AI schemas for AI-powered features