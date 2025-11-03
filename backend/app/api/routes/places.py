from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas.place import Place
from ...schemas.user import UserPublic
from ...services.places import list_places

router = APIRouter()


@router.get("/nearby", response_model=list[Place], summary="주변 데이트 장소 조회")
async def get_nearby_places(
    latitude: float = Query(..., description="현재 위도"),
    longitude: float = Query(..., description="현재 경도"),
    tags: list[str] | None = Query(default=None, description="관심 태그"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: UserPublic = Depends(get_current_user),
) -> list[Place]:
    selected_tags = tags or current_user.preferences
    return await list_places(db, latitude=latitude, longitude=longitude, tags=selected_tags, limit=limit)
