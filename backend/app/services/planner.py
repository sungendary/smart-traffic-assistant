from __future__ import annotations

from datetime import datetime, date as Date

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


def _prepare_payload(data: dict) -> dict:
    prepared = {**data}
    raw_date = prepared.get("date")
    if isinstance(raw_date, Date):
        prepared["date"] = raw_date.isoformat()
    elif isinstance(raw_date, datetime):
        prepared["date"] = raw_date.date().isoformat()
    elif raw_date is None:
        prepared["date"] = None
    else:
        prepared["date"] = str(raw_date) if raw_date else None
    return prepared


async def create_plan(db: AsyncIOMotorDatabase, couple_id: str, payload: dict) -> dict:
    now = datetime.utcnow()
    payload_dict = _prepare_payload(payload)
    plan_doc = {
        "couple_id": ObjectId(couple_id),
        "title": payload_dict.get("title", ""),
        "date": payload_dict.get("date"),
        "emotion_goal": payload_dict.get("emotion_goal"),
        "budget_range": payload_dict.get("budget_range"),
        "stops": payload_dict.get("stops", []),
        "notes": payload_dict.get("notes", ""),
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
    prepared = _prepare_payload(payload)
    prepared["updated_at"] = datetime.utcnow()
    await db[PLANS_COL].update_one({"_id": obj_id, "couple_id": ObjectId(couple_id)}, {"$set": prepared})
    return await get_plan(db, plan_id, couple_id)


async def delete_plan(db: AsyncIOMotorDatabase, plan_id: str, couple_id: str) -> None:
    try:
        obj_id = ObjectId(plan_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 플랜 ID") from exc
    result = await db[PLANS_COL].delete_one({"_id": obj_id, "couple_id": ObjectId(couple_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="플랜을 찾을 수 없습니다.")
