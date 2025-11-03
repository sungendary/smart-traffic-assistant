from __future__ import annotations

import secrets
import string
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

USERS_COL = "users"
COUPLES_COL = "couples"

CODE_ALPHABET = string.ascii_uppercase + string.digits


def _generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


async def ensure_user(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    try:
        obj_id = ObjectId(user_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 사용자 ID") from exc
    doc = await db[USERS_COL].find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return doc


async def get_couple(db: AsyncIOMotorDatabase, couple_id: str | None) -> dict | None:
    if not couple_id:
        return None
    try:
        obj_id = ObjectId(couple_id)
    except Exception:
        return None
    return await db[COUPLES_COL].find_one({"_id": obj_id})


async def create_couple_for_user(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    now = datetime.utcnow()
    code = _generate_code()
    couple_doc = {
        "invite_code": code,
        "members": [ObjectId(user_id)],
        "created_at": now,
        "updated_at": now,
        "preferences": {
            "tags": [],
            "emotion_goals": [],
            "budget": "medium",
        },
        "settings": {
            "notifications": {
                "email": True,
                "push": False,
            }
        },
    }
    result = await db[COUPLES_COL].insert_one(couple_doc)
    couple_doc["_id"] = result.inserted_id
    await db[USERS_COL].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"couple_id": result.inserted_id}},
    )
    return couple_doc


async def get_or_create_couple(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    user_doc = await ensure_user(db, user_id)
    couple = await get_couple(db, user_doc.get("couple_id"))
    if couple:
        return couple
    return await create_couple_for_user(db, user_id)


async def regenerate_invite_code(db: AsyncIOMotorDatabase, couple_id: str) -> str:
    code = _generate_code()
    await db[COUPLES_COL].update_one(
        {"_id": ObjectId(couple_id)},
        {"$set": {"invite_code": code, "updated_at": datetime.utcnow()}},
    )
    return code


async def join_couple_by_code(db: AsyncIOMotorDatabase, user_id: str, code: str) -> dict:
    couple = await db[COUPLES_COL].find_one({"invite_code": code})
    if not couple:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="초대 코드를 찾을 수 없습니다.")

    if ObjectId(user_id) in couple.get("members", []):
        return couple

    await db[COUPLES_COL].update_one(
        {"_id": couple["_id"]},
        {"$push": {"members": ObjectId(user_id)}, "$set": {"updated_at": datetime.utcnow()}},
    )
    await db[USERS_COL].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"couple_id": couple["_id"], "updated_at": datetime.utcnow()}},
    )
    couple["members"].append(ObjectId(user_id))
    return couple


async def update_preferences(db: AsyncIOMotorDatabase, couple_id: str, prefs: dict) -> dict:
    await db[COUPLES_COL].update_one(
        {"_id": ObjectId(couple_id)},
        {"$set": {"preferences": prefs, "updated_at": datetime.utcnow()}},
    )
    return await get_couple(db, couple_id)
