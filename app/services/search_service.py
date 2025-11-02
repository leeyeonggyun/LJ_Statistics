from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from datetime import date, timedelta
from app.models.search_result import SearchResult
from app.services.youtube_client import search_channels
import logging

logger = logging.getLogger(__name__)


async def get_search_from_db(
    session: AsyncSession,
    query: str,
    max_results: int
) -> dict | None:
    today = date.today()

    result = await session.execute(
        select(SearchResult)
        .where(
            SearchResult.search_query == query,
            SearchResult.search_date == today,
            SearchResult.max_results == max_results
        )
    )
    search_result = result.scalar_one_or_none()

    if search_result:
        logger.info(f"Found cached search result in DB for query: {query}")
        return {
            "query": query,
            "result_count": search_result.result_count,
            "channels": search_result.channels_data,
            "nextPageToken": None
        }

    return None


async def save_search_to_db(
    session: AsyncSession,
    query: str,
    max_results: int,
    channels: list
):
    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    await session.execute(
        delete(SearchResult).where(SearchResult.search_date < seven_days_ago)
    )

    search_result = SearchResult(
        search_query=query,
        search_date=today,
        max_results=max_results,
        result_count=len(channels),
        channels_data=channels
    )
    session.add(search_result)
    await session.commit()

    logger.info(f"Saved search result to DB for query: {query}")


async def search_channels_with_cache(
    session: AsyncSession,
    query: str,
    max_results: int = 150,
    page_token: str = None
) -> dict:
    if page_token:
        result = await search_channels(q=query, max_results=max_results, page_token=page_token)
        return {
            "query": query,
            "result_count": len(result["channels"]),
            "channels": result["channels"],
            "nextPageToken": result.get("nextPageToken")
        }

    cached_result = await get_search_from_db(session, query, max_results)
    if cached_result:
        return cached_result

    result = await search_channels(q=query, max_results=max_results, page_token=page_token)
    channels = result["channels"]

    await save_search_to_db(session, query, max_results, channels)

    return {
        "query": query,
        "result_count": len(channels),
        "channels": channels,
        "nextPageToken": result.get("nextPageToken")
    }
