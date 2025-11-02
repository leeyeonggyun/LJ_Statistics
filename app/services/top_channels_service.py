
import asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.youtube_client import get_channels_by_names
from app.services.channel_names import CHANNEL_NAMES
from app.models.top_channel import TopChannel
from app.core.database import async_session_maker
import logging

logger = logging.getLogger(__name__)

COUNTRIES = ["KR", "JP", "US"]

async def update_top_channels():
    from sqlalchemy import func
    from datetime import date, timedelta

    logger.info("Starting top channels update...")

    async with async_session_maker() as session:
        try:
            today = date.today()
            seven_days_ago = today - timedelta(days=7)

            await session.execute(
                delete(TopChannel).where(func.date(TopChannel.created_at) == today)
            )
            await session.execute(
                delete(TopChannel).where(func.date(TopChannel.created_at) < seven_days_ago)
            )
            await session.commit()
            logger.info("Cleared today's and old top channels data")

            for country_code in COUNTRIES:
                logger.info(f"Fetching top channels for {country_code}...")
                channel_names = CHANNEL_NAMES.get(country_code, [])
                channels = await get_channels_by_names(channel_names)

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

                logger.info(f"Saved {len(channels)} channels for {country_code}")

            await session.commit()
            logger.info("Top channels update completed successfully!")

        except Exception as e:
            logger.error(f"Error updating top channels: {e}")
            await session.rollback()
            raise


async def get_top_channels_from_db(session: AsyncSession) -> dict:
    from sqlalchemy import select, func
    from datetime import date

    today = date.today()

    result = await session.execute(
        select(TopChannel)
        .where(func.date(TopChannel.created_at) == today)
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

    return grouped


async def has_today_data(session: AsyncSession) -> bool:
    from sqlalchemy import select, func
    from datetime import date

    today = date.today()

    result = await session.execute(
        select(func.count(TopChannel.id))
        .where(func.date(TopChannel.created_at) == today)
    )
    count = result.scalar()
    return count > 0
