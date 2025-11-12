"""
MongoDB 지오스패셜 쿼리 테스트
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_mongodb_geospatial_query():
    """MongoDB 지오스패셜 쿼리 테스트"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    collection = db.test_places
    
    try:
        # 지오스패셜 인덱스 생성 (이미 있으면 무시됨)
        try:
            await collection.create_index([("location", "2dsphere")])
        except Exception:
            pass  # 인덱스가 이미 존재할 수 있음
        
        # 테스트 장소 데이터 삽입
        test_place = {
            "name": "테스트 장소",
            "location": {
                "type": "Point",
                "coordinates": [126.9780, 37.5665]  # [longitude, latitude]
            }
        }
        await collection.insert_one(test_place)
        
        # 근처 장소 조회 (서울시청 기준 1km 반경)
        nearby_places = await collection.find({
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [126.9780, 37.5665]
                    },
                    "$maxDistance": 1000  # 1km
                }
            }
        }).to_list(length=10)
        
        assert len(nearby_places) > 0
        
    finally:
        # 테스트 데이터 정리
        await collection.delete_many({"name": "테스트 장소"})
        client.close()

