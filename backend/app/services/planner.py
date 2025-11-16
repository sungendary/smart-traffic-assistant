from __future__ import annotations

from datetime import date, datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

PLANS_COL = "plans"


def _normalize_plan(doc: dict) -> dict:
    doc = {**doc}
    doc["id"] = str(doc.pop("_id"))
    doc["couple_id"] = str(doc["couple_id"])
    for stop in doc.get("stops", []):
        if "place_id" in stop:
            stop["place_id"] = str(stop["place_id"])
    return doc


def _ensure_datetime(value: datetime | date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise TypeError(f"Invalid date string: {value!r}") from exc
    raise TypeError(f"Unsupported date value: {type(value)!r}")


async def create_plan(db: AsyncIOMotorDatabase, couple_id: str, payload: dict) -> dict:
    now = datetime.utcnow()
    plan_doc = {
        "couple_id": ObjectId(couple_id),
        "title": payload.get("title", ""),
        "date": _ensure_datetime(payload.get("date")),
        "emotion_goal": payload.get("emotion_goal"),
        "budget_range": payload.get("budget_range"),
        "stops": payload.get("stops", []),
        "notes": payload.get("notes", ""),
        "created_at": now,
        "updated_at": now,
    }
    result = await db[PLANS_COL].insert_one(plan_doc)
    plan_doc["_id"] = result.inserted_id
    return _normalize_plan(plan_doc)


async def list_plans(db: AsyncIOMotorDatabase, couple_id: str) -> list[dict]:
    cursor = db[PLANS_COL].find({"couple_id": ObjectId(couple_id)}).sort("date", 1)
    plans: list[dict] = []
    async for doc in cursor:
        plans.append(_normalize_plan(doc))
    return plans


async def get_plan(db: AsyncIOMotorDatabase, plan_id: str, couple_id: str) -> dict:
    try:
        obj_id = ObjectId(plan_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc
    doc = await db[PLANS_COL].find_one({"_id": obj_id, "couple_id": ObjectId(couple_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="플랜을 찾을 수 없습니다.")
    return _normalize_plan(doc)


async def update_plan(db: AsyncIOMotorDatabase, plan_id: str, couple_id: str, payload: dict) -> dict:
    try:
        obj_id = ObjectId(plan_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc
    if "date" in payload:
        payload["date"] = _ensure_datetime(payload["date"])
    payload["updated_at"] = datetime.utcnow()
    await db[PLANS_COL].update_one({"_id": obj_id, "couple_id": ObjectId(couple_id)}, {"$set": payload})
    return await get_plan(db, plan_id, couple_id)


async def delete_plan(db: AsyncIOMotorDatabase, plan_id: str, couple_id: str) -> None:
    try:
        obj_id = ObjectId(plan_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc
    result = await db[PLANS_COL].delete_one({"_id": obj_id, "couple_id": ObjectId(couple_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="플랜을 찾을 수 없습니다.")
