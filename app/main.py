
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.settings import settings
from app.core.logging import setup_logging
from app.api.endpoints import health as health_ep
from app.api.endpoints import search as search_ep
from app.api.endpoints import top_channels as top_channels_ep
from app.services.top_channels_service import update_top_channels

setup_logging("INFO")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import engine, Base
    from app.models import TopChannel

    logger.info("Recreating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")

    logger.info("Starting scheduler...")
    scheduler.add_job(update_top_channels, 'cron', hour=3, minute=0)
    scheduler.start()
    logger.info("Scheduler started. Top channels will update daily at 3 AM.")

    try:
        logger.info("Running initial top channels update...")
        await update_top_channels()
    except Exception as e:
        logger.error(f"Initial top channels update failed: {e}")

    yield

    logger.info("Shutting down scheduler...")
    scheduler.shutdown()

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_ep.router)
app.include_router(search_ep.router)
app.include_router(top_channels_ep.router)

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
async def root():
    index_path = static_path / "index.html"
    return FileResponse(index_path)
