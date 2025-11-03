from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from ..core.security import get_password_hash, verify_password
from ..schemas.user import UserCreate, UserLogin, UserPublic

USERS_COLLECTION = "users"


async def find_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await db[USERS_COLLECTION].find_one({"email": email})


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
    try:
        object_id = ObjectId(user_id)
    except Exception as exc:  # pragma: no cover - 잘못된 ObjectId
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 사용자 ID 형식입니다.") from exc
    return await db[USERS_COLLECTION].find_one({"_id": object_id})


def document_to_user(doc: dict) -> UserPublic:
    return UserPublic(
        id=str(doc["_id"]),
        email=doc["email"],
        nickname=doc.get("nickname", ""),
        email_verified=doc.get("email_verified", False),
        created_at=doc.get("created_at", datetime.utcnow()),
        preferences=doc.get("preferences", []),
    )


async def create_user(db: AsyncIOMotorDatabase, payload: UserCreate) -> UserPublic:
    existing = await find_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다.")

    now = datetime.utcnow()
    user_doc = {
        "email": payload.email,
        "password_hash": get_password_hash(payload.password),
        "nickname": payload.nickname,
        "preferences": payload.preferences or [],
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[USERS_COLLECTION].insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return document_to_user(user_doc)


async def authenticate_user(db: AsyncIOMotorDatabase, payload: UserLogin) -> dict:
    user_doc = await find_user_by_email(db, payload.email)
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    return user_doc


async def update_user_password(db: AsyncIOMotorDatabase, user_id: str, new_password: str) -> UserPublic:
    hashed = get_password_hash(new_password)
    doc = await db[USERS_COLLECTION].find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hashed, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return document_to_user(doc)
