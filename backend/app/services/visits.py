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
    return doc


async def add_visit(db: AsyncIOMotorDatabase, couple_id: str, user_id: str, payload: dict) -> dict:
    now = datetime.utcnow()
    try:
        plan_id = ObjectId(payload["plan_id"]) if payload.get("plan_id") else None
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc

    doc = {
        "couple_id": ObjectId(couple_id),
        "user_id": ObjectId(user_id),
        "plan_id": plan_id,
        "place_id": payload.get("place_id"),
        "place_name": payload.get("place_name"),
        "visited_at": payload.get("visited_at", now.isoformat()),
        "emotion": payload.get("emotion"),
        "tags": payload.get("tags", []),
        "memo": payload.get("memo", ""),
        "rating": payload.get("rating"),
        "created_at": now,
    }
    result = await db[VISITS_COL].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _normalize(doc)


async def list_visits(db: AsyncIOMotorDatabase, couple_id: str, limit: int = 50) -> list[dict]:
    cursor = db[VISITS_COL].find({"couple_id": ObjectId(couple_id)}).sort("visited_at", -1).limit(limit)
    items: list[dict] = []
    async for doc in cursor:
        items.append(_normalize(doc))
    return items
