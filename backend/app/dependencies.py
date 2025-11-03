from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from .db.mongo import MongoConnectionManager
from .db.redis import RedisConnectionManager


async def get_mongo_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    db = MongoConnectionManager.get_database()
    yield db


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = RedisConnectionManager.get_client()
    try:
        yield client
    finally:
        # 싱글톤으로 유지하므로 종료하지 않음
        pass
