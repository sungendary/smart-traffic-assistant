from datetime import datetime

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import ReportResponse, UserPublic
from ...services.couples import get_or_create_couple
from ...services.reports import build_monthly_report

router = APIRouter()


@router.get("/monthly", response_model=ReportResponse)
async def get_monthly_report(
    month: str = Query(default_factory=lambda: datetime.utcnow().strftime("%Y-%m")),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ReportResponse:
    couple = await get_or_create_couple(db, current_user.id)
    report = await build_monthly_report(db, str(couple["_id"]), month)
    return ReportResponse(**report)
