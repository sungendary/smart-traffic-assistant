from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

CHALLENGE_PLACES_COL = "challenge_places"


def _normalize(doc: dict) -> dict:
    doc = {**doc}
    doc["id"] = str(doc.pop("_id"))
    return doc


async def create_challenge_place(db: AsyncIOMotorDatabase, payload: dict) -> dict:
    """챌린지 장소 생성"""
    now = datetime.utcnow()
    doc = {
        "name": payload["name"],
        "description": payload["description"],
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "address": payload["address"],
        "tags": payload.get("tags", []),
        "badge_reward": payload["badge_reward"],
        "points_reward": payload.get("points_reward", 500),
        "active": payload.get("active", True),
        "created_at": now,
        "updated_at": now,
    }
    result = await db[CHALLENGE_PLACES_COL].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _normalize(doc)


async def get_challenge_place_by_id(db: AsyncIOMotorDatabase, place_id: str) -> dict | None:
    """챌린지 장소 ID로 조회"""
    try:
        obj_id = ObjectId(place_id)
    except Exception:
        return None
    doc = await db[CHALLENGE_PLACES_COL].find_one({"_id": obj_id})
    if doc:
        return _normalize(doc)
    return None


async def list_challenge_places(db: AsyncIOMotorDatabase, active_only: bool = True) -> list[dict]:
    """챌린지 장소 목록 조회"""
    query = {"active": True} if active_only else {}
    cursor = db[CHALLENGE_PLACES_COL].find(query).sort("created_at", 1)
    items: list[dict] = []
    async for doc in cursor:
        items.append(_normalize(doc))
    return items


async def update_challenge_place(db: AsyncIOMotorDatabase, place_id: str, payload: dict) -> dict:
    """챌린지 장소 수정"""
    try:
        obj_id = ObjectId(place_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 장소 ID")
    
    update_data = {k: v for k, v in payload.items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 데이터가 없습니다.")
    
    update_data["updated_at"] = datetime.utcnow()
    result = await db[CHALLENGE_PLACES_COL].update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 장소를 찾을 수 없습니다.")
    
    doc = await db[CHALLENGE_PLACES_COL].find_one({"_id": obj_id})
    return _normalize(doc)


async def delete_challenge_place(db: AsyncIOMotorDatabase, place_id: str) -> bool:
    """챌린지 장소 삭제 (실제 삭제 대신 active=False로 설정)"""
    try:
        obj_id = ObjectId(place_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 장소 ID")
    
    result = await db[CHALLENGE_PLACES_COL].update_one(
        {"_id": obj_id},
        {"$set": {"active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 장소를 찾을 수 없습니다.")
    
    return True





