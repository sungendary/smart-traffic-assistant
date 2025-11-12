"""
MongoDB CRUD 작업 테스트
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_mongodb_create_read():
    """MongoDB 생성 및 조회 테스트"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    collection = db.test_collection
    
    try:
        # 데이터 생성
        test_doc = {
            "_id": ObjectId(),
            "name": "테스트 문서",
            "value": 123
        }
        result = await collection.insert_one(test_doc)
        assert result.inserted_id == test_doc["_id"]
        
        # 데이터 조회
        found = await collection.find_one({"_id": test_doc["_id"]})
        assert found is not None
        assert found["name"] == "테스트 문서"
        assert found["value"] == 123
        
    finally:
        # 테스트 데이터 정리
        await collection.delete_one({"_id": test_doc["_id"]})
        client.close()


@pytest.mark.asyncio
async def test_mongodb_update_delete():
    """MongoDB 수정 및 삭제 테스트"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    collection = db.test_collection
    
    try:
        # 데이터 생성
        test_doc = {"name": "업데이트 테스트", "value": 100}
        result = await collection.insert_one(test_doc)
        doc_id = result.inserted_id
        
        # 데이터 수정
        await collection.update_one(
            {"_id": doc_id},
            {"$set": {"value": 200}}
        )
        
        # 수정 확인
        updated = await collection.find_one({"_id": doc_id})
        assert updated["value"] == 200
        
        # 데이터 삭제
        delete_result = await collection.delete_one({"_id": doc_id})
        assert delete_result.deleted_count == 1
        
        # 삭제 확인
        deleted = await collection.find_one({"_id": doc_id})
        assert deleted is None
        
    finally:
        client.close()

