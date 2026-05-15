"""Search endpoints for notes, journals, and indexed documents."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest, current_user: User = Depends(get_current_user)):
    return await SearchService().search(current_user.id, payload)
