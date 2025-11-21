from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import ReportResponse, SavedReport, UserPublic
from ...services.couples import get_or_create_couple
from ...services.reports import build_monthly_report

router = APIRouter()
REPORTS_COL = "saved_reports"


@router.get("/monthly", response_model=ReportResponse)
async def get_monthly_report(
    month: str = Query(default_factory=lambda: datetime.utcnow().strftime("%Y-%m")),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ReportResponse:
    couple = await get_or_create_couple(db, current_user.id)
    report = await build_monthly_report(db, str(couple["_id"]), month, include_summary=False)
    return ReportResponse(**report)


@router.post("/monthly/summary", response_model=ReportResponse)
async def generate_monthly_summary(
    month: str = Query(default_factory=lambda: datetime.utcnow().strftime("%Y-%m")),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ReportResponse:
    couple = await get_or_create_couple(db, current_user.id)
    report = await build_monthly_report(db, str(couple["_id"]), month, include_summary=True)
    return ReportResponse(**report)


@router.post("/monthly/save", response_model=SavedReport)
async def save_monthly_report(
    month: str = Query(default_factory=lambda: datetime.utcnow().strftime("%Y-%m")),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    report_data: ReportResponse | None = Body(None),
) -> SavedReport:
    couple = await get_or_create_couple(db, current_user.id)
    couple_id = str(couple["_id"])
    
    # 리포트 데이터가 제공되고 summary가 있으면 재사용 (LLM 호출 방지)
    if report_data and report_data.summary:
        report_data_dict = report_data.model_dump()
    else:
        # 리포트 데이터가 없거나 summary가 없으면 새로 생성
        report_data_dict = await build_monthly_report(db, couple_id, month, include_summary=True)
    
    # 기존 리포트가 있는지 확인
    existing = await db[REPORTS_COL].find_one({
        "couple_id": ObjectId(couple_id),
        "month": month,
    })
    
    now = datetime.utcnow()
    if existing:
        # 업데이트
        await db[REPORTS_COL].update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    **report_data_dict,
                    "updated_at": now,
                }
            }
        )
        saved_doc = await db[REPORTS_COL].find_one({"_id": existing["_id"]})
    else:
        # 새로 생성
        doc = {
            "couple_id": ObjectId(couple_id),
            **report_data_dict,
            "created_at": now,
            "updated_at": now,
        }
        result = await db[REPORTS_COL].insert_one(doc)
        saved_doc = await db[REPORTS_COL].find_one({"_id": result.inserted_id})
    
    saved_doc["_id"] = str(saved_doc["_id"])
    saved_doc["couple_id"] = str(saved_doc["couple_id"])
    return SavedReport(**saved_doc)


@router.get("/saved", response_model=list[SavedReport])
async def get_saved_reports(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[SavedReport]:
    couple = await get_or_create_couple(db, current_user.id)
    couple_id = str(couple["_id"])
    
    cursor = db[REPORTS_COL].find(
        {"couple_id": ObjectId(couple_id)}
    ).sort("month", -1)
    
    reports = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["couple_id"] = str(doc["couple_id"])
        reports.append(SavedReport(**doc))
    
    return reports


@router.get("/saved/{report_id}", response_model=SavedReport)
async def get_saved_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> SavedReport:
    couple = await get_or_create_couple(db, current_user.id)
    couple_id = str(couple["_id"])
    
    try:
        doc = await db[REPORTS_COL].find_one({
            "_id": ObjectId(report_id),
            "couple_id": ObjectId(couple_id),
        })
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다.")
    
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="리포트를 찾을 수 없습니다.")
    
    doc["_id"] = str(doc["_id"])
    doc["couple_id"] = str(doc["couple_id"])
    return SavedReport(**doc)
