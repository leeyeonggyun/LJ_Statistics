
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.settings import settings
from app.core.logging import setup_logging
from app.api.endpoints import health as health_ep
from app.api.endpoints import search as search_ep

setup_logging("INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

app.include_router(health_ep.router)
app.include_router(search_ep.router)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
async def root():
    # Serve the HTML page
    index_path = static_path / "index.html"
    return FileResponse(index_path)
