from fastapi import APIRouter, Depends, Path
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import PlanCreate, PlanOut, PlanUpdate, UserPublic
from ...services.couples import get_or_create_couple
from ...services.planner import create_plan, delete_plan, list_plans, update_plan

router = APIRouter()


@router.get("/plans", response_model=list[PlanOut])
async def list_my_plans(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[PlanOut]:
    couple = await get_or_create_couple(db, current_user.id)
    plans = await list_plans(db, str(couple["_id"]))
    return [PlanOut(**plan) for plan in plans]


@router.post("/plans", response_model=PlanOut)
async def create_new_plan(
    payload: PlanCreate,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> PlanOut:
    couple = await get_or_create_couple(db, current_user.id)
    plan = await create_plan(db, str(couple["_id"]), payload.model_dump(exclude_none=True))
    return PlanOut(**plan)


@router.put("/plans/{plan_id}", response_model=PlanOut)
async def update_existing_plan(
    payload: PlanUpdate,
    plan_id: str = Path(..., description="플랜 ID"),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> PlanOut:
    couple = await get_or_create_couple(db, current_user.id)
    plan = await update_plan(db, plan_id, str(couple["_id"]), payload.model_dump(exclude_none=True))
    return PlanOut(**plan)


@router.delete("/plans/{plan_id}")
async def delete_existing_plan(
    plan_id: str = Path(..., description="플랜 ID"),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> dict:
    couple = await get_or_create_couple(db, current_user.id)
    await delete_plan(db, plan_id, str(couple["_id"]))
    return {"status": "deleted"}
