from redis.asyncio import Redis

from ..core.config import settings


class RedisConnectionManager:
    client: Redis | None = None

    @classmethod
    def get_client(cls) -> Redis:
        if cls.client is None:
            cls.client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        return cls.client

    @classmethod
    async def close(cls) -> None:
        if cls.client:
            await cls.client.close()
            cls.client = None
