from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    # A failing DB raises here and surfaces as a 500: the service is not healthy
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
