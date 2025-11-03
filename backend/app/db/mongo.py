from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..core.config import settings


class MongoConnectionManager:
    client: AsyncIOMotorClient | None = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        return cls.client

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        return cls.get_client()[settings.mongodb_db]

    @classmethod
    async def close(cls) -> None:
        if cls.client:
            cls.client.close()
            cls.client = None
