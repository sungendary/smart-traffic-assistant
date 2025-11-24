from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...core.config import settings
from ...dependencies import get_mongo_db
from ...schemas import (
    ChallengeCategoryCreate,
    ChallengeCategoryOut,
    ChallengeCategoryUpdate,
    ChallengePlaceCreate,
    ChallengePlaceOut,
    ChallengePlaceUpdate,
    UserPublic,
)
from ...services.challenge_categories import (
    create_challenge_category,
    delete_challenge_category,
    get_challenge_category_by_id,
    list_challenge_categories,
    update_challenge_category,
)
from ...services.challenge_places import (
    create_challenge_place,
    delete_challenge_place,
    get_challenge_place_by_id,
    list_challenge_places,
    update_challenge_place,
)

router = APIRouter()


def check_admin(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    """관리자 권한 확인 (환경 변수 ADMIN_EMAIL로 체크)"""
    admin_email = getattr(settings, "admin_email", "").strip()
    if admin_email and current_user.email != admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


@router.post("/challenge-places", response_model=ChallengePlaceOut)
async def create_challenge_place_endpoint(
    payload: ChallengePlaceCreate,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengePlaceOut:
    """챌린지 장소 생성"""
    doc = await create_challenge_place(db, payload.model_dump())
    return ChallengePlaceOut(**doc)


@router.get("/challenge-places", response_model=list[ChallengePlaceOut])
async def list_challenge_places_endpoint(
    active_only: bool = True,
    category_id: str | None = None,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[ChallengePlaceOut]:
    """챌린지 장소 목록 조회"""
    places = await list_challenge_places(db, active_only=active_only, category_id=category_id)
    return [ChallengePlaceOut(**p) for p in places]


@router.get("/challenge-places/{place_id}", response_model=ChallengePlaceOut)
async def get_challenge_place_endpoint(
    place_id: str,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengePlaceOut:
    """챌린지 장소 상세 조회"""
    place = await get_challenge_place_by_id(db, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 장소를 찾을 수 없습니다.")
    return ChallengePlaceOut(**place)


@router.put("/challenge-places/{place_id}", response_model=ChallengePlaceOut)
async def update_challenge_place_endpoint(
    place_id: str,
    payload: ChallengePlaceUpdate,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengePlaceOut:
    """챌린지 장소 수정"""
    update_data = payload.model_dump(exclude_none=True)
    doc = await update_challenge_place(db, place_id, update_data)
    return ChallengePlaceOut(**doc)


@router.delete("/challenge-places/{place_id}")
async def delete_challenge_place_endpoint(
    place_id: str,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> dict:
    """챌린지 장소 삭제 (active=False로 설정)"""
    await delete_challenge_place(db, place_id)
    return {"message": "챌린지 장소가 삭제되었습니다."}


# 카테고리 엔드포인트
@router.post("/challenge-categories", response_model=ChallengeCategoryOut)
async def create_challenge_category_endpoint(
    payload: ChallengeCategoryCreate,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengeCategoryOut:
    """챌린지 카테고리 생성"""
    doc = await create_challenge_category(db, payload.model_dump())
    return ChallengeCategoryOut(**doc)


@router.get("/challenge-categories", response_model=list[ChallengeCategoryOut])
async def list_challenge_categories_endpoint(
    active_only: bool = True,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[ChallengeCategoryOut]:
    """챌린지 카테고리 목록 조회"""
    categories = await list_challenge_categories(db, active_only=active_only)
    return [ChallengeCategoryOut(**c) for c in categories]


@router.get("/challenge-categories/{category_id}", response_model=ChallengeCategoryOut)
async def get_challenge_category_endpoint(
    category_id: str,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengeCategoryOut:
    """챌린지 카테고리 상세 조회"""
    category = await get_challenge_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 카테고리를 찾을 수 없습니다.")
    return ChallengeCategoryOut(**category)


@router.put("/challenge-categories/{category_id}", response_model=ChallengeCategoryOut)
async def update_challenge_category_endpoint(
    category_id: str,
    payload: ChallengeCategoryUpdate,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengeCategoryOut:
    """챌린지 카테고리 수정"""
    update_data = payload.model_dump(exclude_none=True)
    doc = await update_challenge_category(db, category_id, update_data)
    return ChallengeCategoryOut(**doc)


@router.delete("/challenge-categories/{category_id}")
async def delete_challenge_category_endpoint(
    category_id: str,
    current_user: UserPublic = Depends(check_admin),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> dict:
    """챌린지 카테고리 삭제 (active=False로 설정)"""
    await delete_challenge_category(db, category_id)
    return {"message": "챌린지 카테고리가 삭제되었습니다."}





