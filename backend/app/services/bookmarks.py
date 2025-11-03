from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

BOOKMARKS_COL = "bookmarks"


def _normalize(doc: dict) -> dict:
    doc = {**doc}
    doc["id"] = str(doc.pop("_id"))
    doc["couple_id"] = str(doc["couple_id"])
    doc["user_id"] = str(doc["user_id"])
    return doc


async def add_bookmark(db: AsyncIOMotorDatabase, couple_id: str, user_id: str, payload: dict) -> dict:
    now = datetime.utcnow()
    doc = {
        "couple_id": ObjectId(couple_id),
        "user_id": ObjectId(user_id),
        "place_id": payload.get("place_id"),
        "place_name": payload.get("place_name"),
        "address": payload.get("address"),
        "note": payload.get("note", ""),
        "tags": payload.get("tags", []),
        "created_at": now,
    }
    result = await db[BOOKMARKS_COL].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _normalize(doc)


async def list_bookmarks(db: AsyncIOMotorDatabase, couple_id: str) -> list[dict]:
    cursor = db[BOOKMARKS_COL].find({"couple_id": ObjectId(couple_id)}).sort("created_at", -1)
    items: list[dict] = []
    async for doc in cursor:
        items.append(_normalize(doc))
    return items


async def remove_bookmark(db: AsyncIOMotorDatabase, bookmark_id: str, couple_id: str) -> None:
    try:
        obj_id = ObjectId(bookmark_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 북마크 ID") from exc
    result = await db[BOOKMARKS_COL].delete_one({"_id": obj_id, "couple_id": ObjectId(couple_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="북마크를 찾을 수 없습니다.")
