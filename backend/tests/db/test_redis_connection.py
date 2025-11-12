"""
Redis 연결 테스트
"""
import pytest
from redis.asyncio import Redis

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_redis_connection():
    """Redis 연결 테스트"""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # PING 명령으로 연결 확인
        result = await redis.ping()
        assert result is True
    except Exception as e:
        pytest.fail(f"Redis connection failed: {e}")
    finally:
        await redis.close()


@pytest.mark.asyncio
async def test_redis_basic_operations():
    """Redis 기본 작업 테스트"""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # SET/GET 테스트
        await redis.set("test:key", "test:value")
        value = await redis.get("test:key")
        assert value == "test:value"
        
        # DELETE 테스트
        await redis.delete("test:key")
        value = await redis.get("test:key")
        assert value is None
        
    finally:
        await redis.close()

