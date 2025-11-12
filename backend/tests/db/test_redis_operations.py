"""
Redis 데이터 저장/조회 테스트
"""
import pytest
from redis.asyncio import Redis

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_redis_set_get():
    """Redis SET/GET 테스트"""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # 문자열 저장 및 조회
        await redis.set("test:string", "hello world")
        value = await redis.get("test:string")
        assert value == "hello world"
        
        # TTL 설정
        await redis.setex("test:ttl", 60, "expires in 60 seconds")
        ttl = await redis.ttl("test:ttl")
        assert 0 < ttl <= 60
        
    finally:
        await redis.delete("test:string", "test:ttl")
        await redis.close()


@pytest.mark.asyncio
async def test_redis_hash_operations():
    """Redis Hash 작업 테스트"""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Hash 저장
        await redis.hset("test:hash", mapping={
            "field1": "value1",
            "field2": "value2"
        })
        
        # Hash 조회
        value1 = await redis.hget("test:hash", "field1")
        assert value1 == "value1"
        
        all_fields = await redis.hgetall("test:hash")
        assert all_fields["field1"] == "value1"
        assert all_fields["field2"] == "value2"
        
    finally:
        await redis.delete("test:hash")
        await redis.close()


@pytest.mark.asyncio
async def test_redis_refresh_token_storage():
    """Redis에 Refresh Token 저장 테스트 (실제 사용 시나리오)"""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Refresh Token 저장 (실제 앱에서 사용하는 방식)
        token_key = "auth:refresh:test-token-id"
        user_id = "user123"
        ttl = 1440 * 60  # 24시간
        
        await redis.setex(token_key, ttl, user_id)
        
        # 토큰 조회
        stored_user_id = await redis.get(token_key)
        assert stored_user_id == user_id
        
        # TTL 확인
        remaining_ttl = await redis.ttl(token_key)
        assert remaining_ttl > 0
        
    finally:
        await redis.delete(token_key)
        await redis.close()

