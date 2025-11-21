from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

COUPLES_COL = "couples"
VISITS_COL = "visits"
CHALLENGE_PLACES_COL = "challenge_places"


async def grant_rewards(
    db: AsyncIOMotorDatabase, couple_id: str, challenge_place_id: str
) -> dict[str, int | list[str]]:
    """
    챌린지 완료 시 포인트와 배지를 지급합니다.
    
    Args:
        db: MongoDB 데이터베이스
        couple_id: 커플 ID
        challenge_place_id: 챌린지 장소 ID
    
    Returns:
        지급된 포인트와 배지 정보
    """
    # 챌린지 장소 정보 조회
    try:
        place_obj_id = ObjectId(challenge_place_id)
    except Exception:
        return {"points": 0, "badges": []}
    
    place_doc = await db[CHALLENGE_PLACES_COL].find_one({"_id": place_obj_id})
    if not place_doc:
        return {"points": 0, "badges": []}
    
    points_reward = place_doc.get("points_reward", 500)
    badge_reward = place_doc.get("badge_reward", "")
    
    # 위치 인증, 별점, 리뷰가 모두 완료된 방문 기록 확인
    try:
        couple_obj_id = ObjectId(couple_id)
    except Exception:
        return {"points": 0, "badges": []}
    
    # 보상 지급 전 최종 검증: 위치 인증, 별점, 리뷰가 모두 완료되었는지 확인
    completed_visit = await db[VISITS_COL].find_one({
        "couple_id": couple_obj_id,
        "challenge_place_id": place_obj_id,
        "location_verified": True,
        "review_completed": True,
        "rating": {"$ne": None},
        "memo": {"$ne": ""}
    })
    
    # 커플 정보 조회
    couple_doc = await db[COUPLES_COL].find_one({"_id": couple_obj_id})
    if not couple_doc:
        return {"points": 0, "badges": []}
    
    if not completed_visit:
        # 조건을 만족하지 않으면 지급하지 않음
        current_points = couple_doc.get("points", 0)
        current_badges = couple_doc.get("badges", [])
        return {"points": current_points, "badges": current_badges}
    
    # 이미 보상을 받았는지 확인: 커플의 배지 목록에 해당 배지가 있는지 확인
    current_badges = couple_doc.get("badges", [])
    
    # 배지가 이미 있으면 이미 보상을 받은 것으로 간주
    if badge_reward and badge_reward in current_badges:
        current_points = couple_doc.get("points", 0)
        return {"points": current_points, "badges": current_badges}
    
    # 포인트 및 배지 지급
    current_points = couple_doc.get("points", 0)
    
    new_points = current_points + points_reward
    new_badges = current_badges.copy()
    
    # 배지가 이미 있는지 확인하고 없으면 추가
    if badge_reward and badge_reward not in new_badges:
        new_badges.append(badge_reward)
    
    # 커플 정보 업데이트
    await db[COUPLES_COL].update_one(
        {"_id": couple_obj_id},
        {
            "$set": {
                "points": new_points,
                "badges": new_badges,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"points": new_points, "badges": new_badges}





