from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import UserPublic, VisitCreate, VisitOut
from ...services.couples import get_or_create_couple
from ...services.visits import add_visit, list_visits

router = APIRouter()


@router.get("/", response_model=list[VisitOut])
async def get_recent_visits(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[VisitOut]:
    couple = await get_or_create_couple(db, current_user.id)
    visits = await list_visits(db, str(couple["_id"]))
    return [VisitOut(**v) for v in visits]


@router.post("/checkin", response_model=VisitOut)
async def add_visit_record(
    payload: VisitCreate,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> VisitOut:
    couple = await get_or_create_couple(db, current_user.id)
    visit = await add_visit(db, str(couple["_id"]), current_user.id, payload.model_dump(exclude_none=True))
    return VisitOut(**visit)
