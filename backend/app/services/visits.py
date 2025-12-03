from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

VISITS_COL = "visits"


def _normalize(doc: dict) -> dict:
    doc = {**doc}
    doc["id"] = str(doc.pop("_id"))
    doc["couple_id"] = str(doc["couple_id"])
    doc["user_id"] = str(doc["user_id"])
    if doc.get("plan_id"):
        doc["plan_id"] = str(doc["plan_id"])
    if doc.get("challenge_place_id"):
        doc["challenge_place_id"] = str(doc["challenge_place_id"])
    doc["location_verified"] = doc.get("location_verified", False)
    doc["review_completed"] = doc.get("review_completed", False)
    return doc


async def add_visit(db: AsyncIOMotorDatabase, couple_id: str, user_id: str, payload: dict) -> dict:
    now = datetime.utcnow()
    try:
        plan_id = ObjectId(payload["plan_id"]) if payload.get("plan_id") else None
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc
    
    challenge_place_id = None
    if payload.get("challenge_place_id"):
        try:
            challenge_place_id = ObjectId(payload["challenge_place_id"])
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 챌린지 장소 ID") from exc
    
    rating = payload.get("rating")
    memo = payload.get("memo", "")
    
    # 챌린지 장소인 경우 실제로 위치 인증이 완료되었는지 DB에서 확인
    location_verified = False
    if challenge_place_id:
        couple_obj_id = ObjectId(couple_id)
        # DB에서 실제 위치 인증 완료 여부 확인
        existing_verified_visit = await db[VISITS_COL].find_one({
            "couple_id": couple_obj_id,
            "challenge_place_id": challenge_place_id,
            "location_verified": True
        })
        
        if not existing_verified_visit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="챌린지 장소는 위치 인증이 필요합니다. 먼저 위치 인증을 완료해주세요."
            )
        
        location_verified = True
        
        # 기존 위치 인증 기록이 있으면 업데이트, 없으면 새로 생성
        if existing_verified_visit.get("review_completed", False):
            # 이미 리뷰가 완료된 경우 중복 방지
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 리뷰가 작성된 챌린지입니다."
            )
    
    # 리뷰와 별점이 모두 작성되었는지 확인
    # 위치 인증, 별점, 리뷰 텍스트가 모두 있어야 완료
    review_completed = bool(location_verified and rating is not None and memo.strip())
    
    if challenge_place_id:
        # 챌린지 장소인 경우 기존 방문 기록 업데이트
        couple_obj_id = ObjectId(couple_id)
        existing_visit = await db[VISITS_COL].find_one({
            "couple_id": couple_obj_id,
            "challenge_place_id": challenge_place_id,
            "location_verified": True
        })
        
        if existing_visit:
            # 기존 방문 기록 업데이트
            update_data = {
                "rating": rating,
                "memo": memo,
                "emotion": payload.get("emotion"),
                "tags": payload.get("tags", []),
                "review_completed": review_completed,
            }
            
            result = await db[VISITS_COL].update_one(
                {"_id": existing_visit["_id"]},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # 업데이트된 문서 조회
                updated_doc = await db[VISITS_COL].find_one({"_id": existing_visit["_id"]})
                doc = updated_doc
            else:
                doc = existing_visit
        else:
            # 기존 기록이 없으면 새로 생성 (이론적으로는 발생하지 않아야 함)
            doc = {
                "couple_id": couple_obj_id,
                "user_id": ObjectId(user_id),
                "plan_id": plan_id,
                "place_id": payload.get("place_id"),
                "place_name": payload.get("place_name"),
                "visited_at": payload.get("visited_at", now.isoformat()),
                "emotion": payload.get("emotion"),
                "tags": payload.get("tags", []),
                "memo": memo,
                "rating": rating,
                "challenge_place_id": challenge_place_id,
                "location_verified": location_verified,
                "review_completed": review_completed,
                "created_at": now,
            }
            result = await db[VISITS_COL].insert_one(doc)
            doc["_id"] = result.inserted_id
    else:
        # 일반 장소인 경우 새로 생성
        doc = {
            "couple_id": ObjectId(couple_id),
            "user_id": ObjectId(user_id),
            "plan_id": plan_id,
            "place_id": payload.get("place_id"),
            "place_name": payload.get("place_name"),
            "visited_at": payload.get("visited_at", now.isoformat()),
            "emotion": payload.get("emotion"),
            "tags": payload.get("tags", []),
            "memo": memo,
            "rating": rating,
            "challenge_place_id": challenge_place_id,
            "location_verified": location_verified,
            "review_completed": review_completed,
            "created_at": now,
        }
        result = await db[VISITS_COL].insert_one(doc)
        doc["_id"] = result.inserted_id
    
    # 리뷰 완료 시 보상 지급 (위치 인증, 별점, 리뷰 모두 완료된 경우)
    if review_completed and challenge_place_id:
        from .rewards import grant_rewards
        await grant_rewards(db, couple_id, str(challenge_place_id))
    
    return _normalize(doc)


async def list_visits(db: AsyncIOMotorDatabase, couple_id: str, limit: int = 50) -> list[dict]:
    cursor = db[VISITS_COL].find({"couple_id": ObjectId(couple_id)}).sort("visited_at", -1).limit(limit)
    items: list[dict] = []
    async for doc in cursor:
        items.append(_normalize(doc))
    return items
