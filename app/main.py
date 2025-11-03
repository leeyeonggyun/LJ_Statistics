
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.logging import setup_logging
from app.api.endpoints import health as health_ep
from app.api.endpoints import search as search_ep
from app.api.endpoints import top_channels as top_channels_ep

setup_logging("INFO")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import engine, Base

    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")

    yield

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
