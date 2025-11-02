
from fastapi import APIRouter, Query
from app.services.youtube_client import search_videos_recent_week, search_channels
from app.core.redis import cache_get, cache_set
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

SEARCH_CACHE_TTL = 3600  # 1 hour in seconds

@router.get("/search/summary")
async def search_summary(q: str = Query(..., min_length=1)):
    data = await search_videos_recent_week(q=q, max_results=25)
    count = len(data.get("items", []))
    return {"query": q, "result_count": count}

@router.get("/search/channels")
async def search_channels_endpoint(
    q: str = Query(..., min_length=1, description="Search keyword"),
    max_results: int = Query(default=150, ge=1, le=150, description="Maximum number of results"),
    page_token: str = Query(default=None, description="Page token for pagination")
) -> Dict[str, Any]:
    """
    Search for YouTube channels by keyword and return them sorted by subscriber count
    Fetches multiple pages to find channels matching the keyword in title, description, or tags
    """
    # Try to get from cache first
    cache_key = f"search_channels:{q}:{max_results}:{page_token or 'none'}"
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Returning cached search results for query: {q}")
        return cached_data

    # If not in cache, perform search
    result = await search_channels(q=q, max_results=max_results, page_token=page_token)
    response = {
        "query": q,
        "result_count": len(result["channels"]),
        "channels": result["channels"],
        "nextPageToken": result.get("nextPageToken")
    }

    # Cache the result for 1 hour
    await cache_set(cache_key, response, ttl=SEARCH_CACHE_TTL)
    logger.info(f"Cached search results for query: {q}")

    return response
