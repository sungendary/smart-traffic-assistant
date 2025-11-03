from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.security import get_password_hash, verify_password
from ..schemas.user import UserCreate, UserLogin, UserPublic

USERS_COLLECTION = "users"


async def find_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await db[USERS_COLLECTION].find_one({"email": email})


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str | None) -> dict | None:
    if not user_id:
        return None
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        return None
    return await db[USERS_COLLECTION].find_one({"_id": obj_id})


def document_to_user(doc: dict) -> UserPublic:
    return UserPublic(
        id=str(doc["_id"]),
        email=doc["email"],
        nickname=doc.get("nickname", ""),
        email_verified=doc.get("email_verified", False),
        created_at=doc.get("created_at", datetime.utcnow()),
        preferences=doc.get("preferences", []),
        couple_id=str(doc.get("couple_id")) if doc.get("couple_id") else None,
    )


async def create_user(db: AsyncIOMotorDatabase, payload: UserCreate) -> UserPublic:
    existing = await find_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다.")

    now = datetime.utcnow()
    doc = {
        "email": payload.email,
        "password_hash": get_password_hash(payload.password),
        "nickname": payload.nickname,
        "preferences": payload.preferences or [],
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[USERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return document_to_user(doc)


async def authenticate_user(db: AsyncIOMotorDatabase, payload: UserLogin) -> dict:
    user_doc = await find_user_by_email(db, payload.email)
    if not user_doc or not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return user_doc
