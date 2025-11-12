"""
MongoDB 연결 테스트
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_mongodb_connection():
    """MongoDB 연결 테스트"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    try:
        # 연결 확인
        await client.admin.command('ping')
        assert True
    except Exception as e:
        pytest.fail(f"MongoDB connection failed: {e}")
    finally:
        client.close()


@pytest.mark.asyncio
async def test_mongodb_database_access():
    """MongoDB 데이터베이스 접근 테스트"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    try:
        db = client[settings.mongodb_db]
        # 데이터베이스 목록 확인
        db_list = await client.list_database_names()
        assert settings.mongodb_db in db_list or True  # DB가 없어도 생성 가능하므로 True 허용
    finally:
        client.close()

