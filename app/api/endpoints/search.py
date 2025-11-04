
from fastapi import APIRouter, Query, Depends
from app.services.youtube_client import search_videos_recent_week
from app.services.search_service import search_channels_with_cache
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

@router.get("/search/summary")
async def search_summary(q: str = Query(..., min_length=1)):
    data = await search_videos_recent_week(q=q, max_results=25)
    count = len(data.get("items", []))
    return {"query": q, "result_count": count}

@router.get("/search/channels")
async def search_channels_endpoint(
    q: str = Query(..., min_length=1, description="Search keyword"),
    max_results: int = Query(default=100, ge=1, le=100, description="Maximum number of results"),
    page_token: str = Query(default=None, description="Page token for pagination"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    return await search_channels_with_cache(db, q, max_results, page_token)
