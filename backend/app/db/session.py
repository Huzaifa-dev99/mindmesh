"""
Database session management.

This module handles database connection and session management using SQLAlchemy.
It provides dependency injection for FastAPI routes and manages database transactions.

Architecture decisions:
- Uses SQLAlchemy async engine for better performance with FastAPI
- Implements session lifecycle management with context managers
- Provides FastAPI dependency injection for database sessions
- Prepared for connection pooling and transaction management
- Separates engine creation from session management for testability
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from app.core.config import settings

# Create async engine with connection pooling
# Uses PostgreSQL async driver (asyncpg) for optimal performance
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,  # SQL query logging in development
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI routes.

    Provides a database session that is automatically closed after the request.
    Use as a FastAPI dependency: `db: AsyncSession = Depends(get_db)`

    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()  # Commit on successful request
        except Exception:
            await session.rollback()  # Rollback on error
            raise
        finally:
            await session.close()  # Always close the session

# TODO: Add database initialization function
# async def init_db():
#     """Create all tables defined in models."""
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

# TODO: Add database health check
# async def check_db_connection() -> bool:
#     """Verify database connectivity."""
#     try:
#         async with engine.begin() as conn:
#             await conn.execute(text("SELECT 1"))
#         return True
#     except Exception:
#         return False