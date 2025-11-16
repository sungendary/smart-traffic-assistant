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
    
    location_verified = payload.get("location_verified", False)
    rating = payload.get("rating")
    memo = payload.get("memo", "")
    
    # 리뷰와 별점이 모두 작성되었는지 확인
    review_completed = bool(location_verified and rating is not None and memo.strip())
    
    # 챌린지 장소인 경우 위치 인증이 필요
    if challenge_place_id and not location_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="챌린지 장소는 위치 인증이 필요합니다."
        )

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
    
    # 리뷰 완료 시 보상 지급
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
