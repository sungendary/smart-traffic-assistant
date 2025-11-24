from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import (
    ChallengeCategoryOut,
    ChallengeProgress,
    ChallengeStatus,
    LocationVerifyRequest,
    LocationVerifyResponse,
    UserPublic,
)
from ...services.challenge_categories import list_challenge_categories
from ...services.challenge_places import get_challenge_place_by_id, list_challenge_places
from ...services.challenges import get_progress
from ...services.couples import calculate_tier, get_couple, get_or_create_couple
from ...services.geolocation import calculate_distance, is_within_radius

router = APIRouter()


@router.get("/categories", response_model=list[ChallengeCategoryOut])
async def list_challenge_categories_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[ChallengeCategoryOut]:
    """챌린지 카테고리 목록 조회 (일반 사용자용)"""
    categories = await list_challenge_categories(db, active_only=True)
    return [ChallengeCategoryOut(**c) for c in categories]


@router.get("/", response_model=list[ChallengeProgress])
async def get_challenge_progress(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[ChallengeProgress]:
    couple = await get_or_create_couple(db, current_user.id)
    progress = await get_progress(db, str(couple["_id"]))
    return [ChallengeProgress(**p) for p in progress]


@router.post("/verify-location", response_model=LocationVerifyResponse)
async def verify_location(
    payload: LocationVerifyRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> LocationVerifyResponse:
    """위치 인증: 사용자 위치가 챌린지 장소 1km 반경 내에 있는지 확인"""
    from bson import ObjectId
    
    challenge_place = await get_challenge_place_by_id(db, payload.challenge_place_id)
    if not challenge_place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챌린지 장소를 찾을 수 없습니다."
        )
    
    if not challenge_place.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 챌린지 장소입니다."
        )
    
    place_lat = challenge_place["latitude"]
    place_lon = challenge_place["longitude"]
    user_lat = payload.latitude
    user_lon = payload.longitude
    
    distance = calculate_distance(user_lat, user_lon, place_lat, place_lon)
    verified = is_within_radius(user_lat, user_lon, place_lat, place_lon, radius_meters=1000)
    
    if verified:
        message = f"위치 인증 성공! ({distance:.0f}m 거리)"
    else:
        message = f"위치 인증 실패. 챌린지 장소로부터 {distance:.0f}m 떨어져 있습니다. (필요: 1km 이내)"
    
    return LocationVerifyResponse(
        verified=verified,
        distance_meters=round(distance, 2),
        message=message
    )


@router.get("/status", response_model=ChallengeStatus)
async def get_challenge_status(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ChallengeStatus:
    """챌린지 상태 조회: 포인트, 배지, 각 챌린지 장소별 진행 상태"""
    from bson import ObjectId
    
    couple = await get_or_create_couple(db, current_user.id)
    couple_id = str(couple["_id"])
    
    # 커플의 포인트와 배지 조회
    couple_doc = await get_couple(db, couple_id)
    points = couple_doc.get("points", 0) if couple_doc else 0
    badges = couple_doc.get("badges", []) if couple_doc else []
    badge_count = len(badges)
    
    # 티어 계산
    tier_info = calculate_tier(badge_count)
    
    # 모든 활성 챌린지 장소 조회
    challenge_places = await list_challenge_places(db, active_only=True)
    
    # 각 챌린지 장소별 완료 여부 확인
    VISITS_COL = "visits"
    challenge_statuses = []
    
    for place in challenge_places:
        place_obj_id = ObjectId(place["id"])
        couple_obj_id = ObjectId(couple_id)
        
        # 해당 챌린지를 완료했는지 확인
        completed_visit = await db[VISITS_COL].find_one({
            "couple_id": couple_obj_id,
            "challenge_place_id": place_obj_id,
            "review_completed": True
        })
        
        # 위치 인증만 완료했는지 확인
        location_verified_visit = await db[VISITS_COL].find_one({
            "couple_id": couple_obj_id,
            "challenge_place_id": place_obj_id,
            "location_verified": True
        })
        
        status_info = {
            "id": place["id"],
            "name": place["name"],
            "description": place["description"],
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "badge_reward": place["badge_reward"],
            "points_reward": place["points_reward"],
            "location_verified": bool(location_verified_visit),
            "review_completed": bool(completed_visit),
        }
        challenge_statuses.append(status_info)
    
    return ChallengeStatus(
        points=points,
        badges=badges,
        challenge_places=challenge_statuses,
        tier=tier_info["tier"],
        tier_name=tier_info["tier_name"],
        badge_count=badge_count,
        next_tier_badges_needed=tier_info["next_tier_badges_needed"],
    )
