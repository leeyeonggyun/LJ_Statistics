
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.top_channels_service import get_top_channels_from_db

router = APIRouter(prefix="/api")

@router.get("/top-channels")
async def get_top_channels(db: AsyncSession = Depends(get_db)):
    result = await get_top_channels_from_db(db)
    return result
