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


def calculate_tier(badge_count: int) -> dict[str, int | str | None]:
    """
    배지 개수에 따라 티어를 계산합니다.
    
    Args:
        badge_count: 커플이 획득한 배지 개수
    
    Returns:
        티어 정보 딕셔너리:
        - tier: 티어 번호 (1-5)
        - tier_name: 티어 이름
        - next_tier_badges_needed: 다음 티어까지 필요한 배지 개수 (마지막 티어면 None)
    """
    if 0 <= badge_count <= 4:
        return {
            "tier": 1,
            "tier_name": "새싹 커플",
            "next_tier_badges_needed": 5 - badge_count,
        }
    elif 5 <= badge_count <= 9:
        return {
            "tier": 2,
            "tier_name": "꽁냥꽁냥 커플",
            "next_tier_badges_needed": 10 - badge_count,
        }
    elif 10 <= badge_count <= 14:
        return {
            "tier": 3,
            "tier_name": "척척 콤비",
            "next_tier_badges_needed": 15 - badge_count,
        }
    elif 15 <= badge_count <= 19:
        return {
            "tier": 4,
            "tier_name": "데이트 장인",
            "next_tier_badges_needed": 20 - badge_count,
        }
    else:  # 20개 이상
        return {
            "tier": 5,
            "tier_name": "전설의 커플",
            "next_tier_badges_needed": None,
        }


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
        "points": 0,
        "badges": [],
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
