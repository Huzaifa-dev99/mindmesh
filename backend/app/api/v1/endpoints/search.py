"""
Placeholder for search endpoints.

Future endpoints:
- GET /search: Unified search across journals and knowledge
- GET /search/suggestions: Search suggestions
- POST /search/advanced: Advanced search with filters
"""

# TODO: Implement unified search functionality
# TODO: Add full-text search capabilities
# TODO: Add vector similarity search
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest, current_user: User = Depends(get_current_user)):
    return await SearchService().search(current_user.id, payload)
