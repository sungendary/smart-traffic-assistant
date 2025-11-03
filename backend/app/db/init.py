from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["users"].create_index("email", unique=True)
    await db["couples"].create_index("invite_code", unique=True)
    await db["bookmarks"].create_index([("couple_id", 1), ("created_at", -1)])
    await db["plans"].create_index([("couple_id", 1), ("date", 1)])
    await db["visits"].create_index([("couple_id", 1), ("visited_at", -1)])
    await db["places"].create_index([("location", "2dsphere")])
