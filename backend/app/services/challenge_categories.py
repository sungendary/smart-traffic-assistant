from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

CHALLENGE_CATEGORIES_COL = "challenge_categories"


def _normalize(doc: dict) -> dict:
    doc = {**doc}
    doc["id"] = str(doc.pop("_id"))
    return doc


async def create_challenge_category(db: AsyncIOMotorDatabase, payload: dict) -> dict:
    """챌린지 카테고리 생성"""
    now = datetime.utcnow()
    doc = {
        "name": payload["name"],
        "description": payload.get("description"),
        "icon": payload.get("icon"),
        "color": payload.get("color"),
        "active": payload.get("active", True),
        "created_at": now,
        "updated_at": now,
    }
    result = await db[CHALLENGE_CATEGORIES_COL].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _normalize(doc)


async def get_challenge_category_by_id(db: AsyncIOMotorDatabase, category_id: str) -> dict | None:
    """챌린지 카테고리 ID로 조회"""
    try:
        obj_id = ObjectId(category_id)
    except Exception:
        return None
    doc = await db[CHALLENGE_CATEGORIES_COL].find_one({"_id": obj_id})
    if doc:
        return _normalize(doc)
    return None


async def list_challenge_categories(db: AsyncIOMotorDatabase, active_only: bool = True) -> list[dict]:
    """챌린지 카테고리 목록 조회"""
    query = {"active": True} if active_only else {}
    cursor = db[CHALLENGE_CATEGORIES_COL].find(query).sort("created_at", 1)
    items: list[dict] = []
    async for doc in cursor:
        items.append(_normalize(doc))
    return items


async def update_challenge_category(db: AsyncIOMotorDatabase, category_id: str, payload: dict) -> dict:
    """챌린지 카테고리 수정"""
    try:
        obj_id = ObjectId(category_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 카테고리 ID")
    
    update_data = {k: v for k, v in payload.items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 데이터가 없습니다.")
    
    update_data["updated_at"] = datetime.utcnow()
    result = await db[CHALLENGE_CATEGORIES_COL].update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 카테고리를 찾을 수 없습니다.")
    
    doc = await db[CHALLENGE_CATEGORIES_COL].find_one({"_id": obj_id})
    return _normalize(doc)


async def delete_challenge_category(db: AsyncIOMotorDatabase, category_id: str) -> bool:
    """챌린지 카테고리 삭제 (실제 삭제 대신 active=False로 설정)"""
    try:
        obj_id = ObjectId(category_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 카테고리 ID")
    
    result = await db[CHALLENGE_CATEGORIES_COL].update_one(
        {"_id": obj_id},
        {"$set": {"active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 카테고리를 찾을 수 없습니다.")
    
    return True

