
from fastapi import APIRouter, Query, Depends
from app.services.search_service import get_trending_channels_with_cache
from app.services.youtube_client import get_i18n_regions
from app.core.database import get_db
from app.core.redis import cache_get, cache_set
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

@router.get("/regions")
async def get_regions_endpoint() -> List[Dict[str, str]]:
    cache_key = "youtube_regions"
    cached_regions = await cache_get(cache_key)

    if cached_regions:
        logger.info("Returning regions from cache")
        return cached_regions

    regions = await get_i18n_regions()
    await cache_set(cache_key, regions, ttl=86400)

    return regions

@router.get("/trending/channels")
async def get_trending_channels_endpoint(
    region_code: str = Query(default="KR", description="Region code (KR, JP, US, etc)"),
    max_results: int = Query(default=50, ge=1, le=50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    return await get_trending_channels_with_cache(db, region_code, max_results)
