from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import ChallengeProgress, UserPublic
from ...services.challenges import get_progress
from ...services.couples import get_or_create_couple

router = APIRouter()


@router.get("/", response_model=list[ChallengeProgress])
async def get_challenge_progress(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[ChallengeProgress]:
    couple = await get_or_create_couple(db, current_user.id)
    progress = await get_progress(db, str(couple["_id"]))
    return [ChallengeProgress(**p) for p in progress]
