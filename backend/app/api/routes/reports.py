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
    name: str | None = Body(None),
) -> SavedReport:
    couple = await get_or_create_couple(db, current_user.id)
    couple_id = str(couple["_id"])
    
    # 리포트 데이터가 제공되고 summary가 있으면 재사용 (LLM 호출 방지)
    if report_data and report_data.summary:
        report_data_dict = report_data.model_dump()
    else:
        # 리포트 데이터가 없거나 summary가 없으면 새로 생성
        report_data_dict = await build_monthly_report(db, couple_id, month, include_summary=True)
    
    # 이름이 제공되면 추가, 없으면 기본값 사용
    if name is not None:
        report_data_dict["name"] = name
    elif "name" not in report_data_dict:
        report_data_dict["name"] = f"{month} 리포트"
    
    now = datetime.utcnow()
    # 날짜별로 여러 리포트를 저장할 수 있도록 항상 새로 생성
    # (같은 날짜에 여러 리포트를 저장하고 싶은 경우를 위해)
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
    # id 필드를 명시적으로 추가하여 프론트엔드에서 사용할 수 있도록 함
    saved_doc["id"] = saved_doc["_id"]
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
    ).sort("created_at", -1)
    
    reports = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["couple_id"] = str(doc["couple_id"])
        # id 필드를 명시적으로 추가하여 프론트엔드에서 사용할 수 있도록 함
        doc["id"] = doc["_id"]
        # name 필드가 없으면 기본값 설정
        if "name" not in doc or not doc["name"]:
            doc["name"] = f"{doc.get('month', '')} 리포트"
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
    # id 필드를 명시적으로 추가하여 프론트엔드에서 사용할 수 있도록 함
    doc["id"] = doc["_id"]
    # name 필드가 없으면 기본값 설정
    if "name" not in doc or not doc["name"]:
        doc["name"] = f"{doc.get('month', '')} 리포트"
    return SavedReport(**doc)
