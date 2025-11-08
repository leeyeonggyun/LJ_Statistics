from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from datetime import date, timedelta
from app.models.search_result import SearchResult
from app.services.youtube_client import get_trending_channels
import logging

logger = logging.getLogger(__name__)


async def get_trending_from_db(
    session: AsyncSession,
    region_code: str,
    max_results: int
) -> dict | None:
    today = date.today()

    result = await session.execute(
        select(SearchResult)
        .where(
            SearchResult.search_query == region_code,
            SearchResult.search_date == today,
            SearchResult.max_results == max_results
        )
    )
    search_result = result.scalar_one_or_none()

    if search_result:
        logger.info(f"Found cached trending channels for region: {region_code}")
        return {
            "regionCode": region_code,
            "result_count": search_result.result_count,
            "channels": search_result.channels_data,
        }

    return None


async def save_trending_to_db(
    session: AsyncSession,
    region_code: str,
    max_results: int,
    channels: list
):
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    await session.execute(
        delete(SearchResult).where(SearchResult.search_date < thirty_days_ago)
    )

    search_result = SearchResult(
        search_query=region_code,
        search_date=today,
        max_results=max_results,
        result_count=len(channels),
        channels_data=channels
    )
    session.add(search_result)
    await session.commit()

    logger.info(f"Saved trending channels to DB for region: {region_code}")


async def get_trending_channels_with_cache(
    session: AsyncSession,
    region_code: str = "KR",
    max_results: int = 50,
) -> dict:
    cached_result = await get_trending_from_db(session, region_code, max_results)
    if cached_result:
        return cached_result

    try:
        result = await get_trending_channels(region_code=region_code, max_results=max_results)
        channels = result["channels"]

        await save_trending_to_db(session, region_code, max_results, channels)

        return {
            "regionCode": region_code,
            "result_count": len(channels),
            "channels": channels,
        }
    except Exception as e:
        logger.error(f"Trending API call failed: {e}")
        return {
            "regionCode": region_code,
            "result_count": 0,
            "channels": [],
            "error": "API 할당량 초과. 잠시 후 다시 시도해주세요."
        }
