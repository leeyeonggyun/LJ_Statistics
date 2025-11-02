
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.top_channels_service import get_top_channels_from_db, update_top_channels

router = APIRouter(prefix="/api")

@router.get("/top-channels")
async def get_top_channels(db: AsyncSession = Depends(get_db)):
    result = await get_top_channels_from_db(db)
    return result

@router.post("/top-channels/update")
async def trigger_update():
    try:
        await update_top_channels()
        return {"status": "success", "message": "Top channels updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
