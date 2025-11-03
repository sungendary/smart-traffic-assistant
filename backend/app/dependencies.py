from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from .db.mongo import MongoConnectionManager
from .db.redis import RedisConnectionManager


async def get_mongo_db() -> AsyncIOMotorDatabase:
    return MongoConnectionManager.get_database()


async def get_redis() -> Redis:
    return RedisConnectionManager.get_client()


async def rate_limit_dependency(_: Redis | None = None) -> None:
    # 추후 레이트리밋 로직을 주입할 자리
    return None
