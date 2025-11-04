
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.top_channels_service import update_top_channels
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        update_top_channels,
        CronTrigger(hour=0, minute=1, timezone='Asia/Seoul'),
        id='update_top_channels',
        name='Update top channels daily at 00:01 KST',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started: Top channels will update daily at 00:01 KST")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")
