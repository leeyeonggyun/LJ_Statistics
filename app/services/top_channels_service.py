
import asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.youtube_client import get_channels_by_ids, get_channels_by_names
from app.services.channel_names import CHANNEL_IDS, CHANNEL_NAMES
from app.models.top_channel import TopChannel
from app.core.database import async_session_maker
from app.core.redis import cache_get, cache_set
import logging

logger = logging.getLogger(__name__)

COUNTRIES = ["KR", "JP", "US"]
CACHE_TTL = 86400

async def update_top_channels():
    from sqlalchemy import func
    from datetime import date, timedelta

    logger.info("Starting top channels update...")

    async with async_session_maker() as session:
        try:
            for country_code in COUNTRIES:
                logger.info(f"Fetching top channels for {country_code}...")

                channel_ids = CHANNEL_IDS.get(country_code, [])

                if channel_ids:
                    logger.info(f"Using {len(channel_ids)} channel IDs for {country_code}")
                    try:
                        channels = await get_channels_by_ids(channel_ids)
                    except Exception as e:
                        logger.error(f"Failed to get channels by IDs for {country_code}: {e}")
                        channels = []
                else:
                    logger.warning(f"No channel IDs found for {country_code}, falling back to name search (expensive!)")
                    logger.warning(f"Please run scripts/collect_channel_ids.py to populate channel IDs")
                    channel_names = CHANNEL_NAMES.get(country_code, [])
                    try:
                        channels = await get_channels_by_names(channel_names)
                    except Exception as e:
                        logger.error(f"Failed to get channels by names for {country_code}: {e}")
                        channels = []

                if not channels:
                    logger.warning(f"No channels retrieved for {country_code}, skipping save")
                    continue

                await session.execute(
                    delete(TopChannel).where(TopChannel.country_code == country_code)
                )
                await session.commit()
                logger.info(f"Cleared all existing data for {country_code}")

                for rank, channel in enumerate(channels, start=1):
                    top_channel = TopChannel(
                        country_code=country_code,
                        channel_id=channel["channelId"],
                        title=channel["title"],
                        description=channel["description"],
                        thumbnail_url=channel["thumbnailUrl"],
                        subscriber_count=channel["subscriberCount"],
                        video_count=channel["videoCount"],
                        view_count=channel["viewCount"],
                        custom_url=channel.get("customUrl", ""),
                        published_at=channel.get("publishedAt", ""),
                        rank=rank
                    )
                    session.add(top_channel)
                await session.commit()

                logger.info(f"Saved {len(channels)} channels for {country_code}")

            logger.info("Top channels update completed successfully!")

        except Exception as e:
            logger.error(f"Error updating top channels: {e}")
            await session.rollback()
            raise


async def get_top_channels_from_db(session: AsyncSession) -> dict:
    from sqlalchemy import select
    from datetime import datetime, date, timezone, timedelta
    from app.core.redis import cache_delete

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    today_kst = now_kst.date()

    cache_key = f"top_channels:{today_kst}"
    cached_data = await cache_get(cache_key)
    if cached_data:
        total_channels = sum(len(cached_data.get(country, [])) for country in ["KR", "JP", "US"])
        if total_channels == 0:
            logger.warning("Cache has empty data, deleting cache")
            await cache_delete(cache_key)
        else:
            logger.info("Returning top channels from cache")
            return cached_data

    today_start_kst = datetime.combine(today_kst, datetime.min.time()).replace(tzinfo=kst)
    today_start_utc = today_start_kst.astimezone(timezone.utc)

    result = await session.execute(
        select(TopChannel)
        .where(TopChannel.created_at >= today_start_utc)
        .order_by(TopChannel.country_code, TopChannel.rank)
    )
    channels = result.scalars().all()

    grouped = {"KR": [], "JP": [], "US": []}
    for channel in channels:
        grouped[channel.country_code].append({
            "rank": channel.rank,
            "channelId": channel.channel_id,
            "title": channel.title,
            "description": channel.description,
            "thumbnailUrl": channel.thumbnail_url,
            "subscriberCount": channel.subscriber_count,
            "videoCount": channel.video_count,
            "viewCount": channel.view_count,
            "customUrl": channel.custom_url,
            "publishedAt": channel.published_at,
            "updatedAt": channel.updated_at.isoformat() if channel.updated_at else None,
        })

    await cache_set(cache_key, grouped, ttl=CACHE_TTL)
    logger.info("Cached top channels data")

    return grouped


async def has_today_data(session: AsyncSession) -> bool:
    from sqlalchemy import select, func
    from datetime import datetime, date, timezone, timedelta

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    today_kst = now_kst.date()

    today_start_kst = datetime.combine(today_kst, datetime.min.time()).replace(tzinfo=kst)
    today_start_utc = today_start_kst.astimezone(timezone.utc)

    result = await session.execute(
        select(func.count(TopChannel.id))
        .where(TopChannel.created_at >= today_start_utc)
    )
    count = result.scalar()
    return count > 0
