from typing import Iterable

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.place import Place

PLACES_COLLECTION = "places"

FALLBACK_PLACES = [
    Place(
        id="sample-1",
        name="한강 공원 야경 피크닉",
        description="야경이 아름다운 한강 공원에서 돗자리 데이트",
        coordinates={"latitude": 37.528, "longitude": 126.932},
        tags=["야경", "피크닉", "야외"],
        rating=4.6,
        source="sample",
    ),
    Place(
        id="sample-2",
        name="조용한 북카페 힐링",
        description="내향 커플을 위한 아늑한 북카페",
        coordinates={"latitude": 37.560, "longitude": 126.975},
        tags=["카페", "실내", "힐링"],
        rating=4.8,
        source="sample",
    ),
]


async def list_places(
    db: AsyncIOMotorDatabase,
    *,
    latitude: float,
    longitude: float,
    tags: Iterable[str] | None = None,
    limit: int = 10,
) -> list[Place]:
    collection = db[PLACES_COLLECTION]
    query: dict = {}

    if tags:
        query["tags"] = {"$in": list(tags)}

    query["location"] = {
        "$near": {
            "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            "$maxDistance": 5000,
        }
    }

    cursor = collection.find(query).limit(limit)
    results: list[Place] = []
    async for doc in cursor:
        results.append(Place.from_mongo(doc))

    if not results:
        return FALLBACK_PLACES[:limit]
    return results


async def get_nearby_places(
    db: AsyncIOMotorDatabase,
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    limit: int = 50,
) -> list[dict]:
    """
    주변 장소를 조회 (딕셔너리 형태로 반환)
    
    Args:
        db: MongoDB 데이터베이스
        lat: 위도
        lon: 경도
        radius_km: 검색 반경 (km)
        limit: 최대 결과 수
    
    Returns:
        장소 정보 리스트 (dict)
    """
    collection = db[PLACES_COLLECTION]
    
    query = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": radius_km * 1000,  # meters
            }
        }
    }
    
    cursor = collection.find(query).limit(limit)
    results = []
    
    async for doc in cursor:
        place_dict = {
            "place_id": str(doc.get("_id", "")),
            "place_name": doc.get("name", ""),
            "description": doc.get("description", ""),
            "category_name": doc.get("category", "기타"),
            "tags": doc.get("tags", []),
            "rating": doc.get("rating", 0.0),
            "coordinates": doc.get("coordinates", {"latitude": lat, "longitude": lon}),
            "address": doc.get("address", ""),
            "phone": doc.get("phone", ""),
        }
        results.append(place_dict)
    
    # 데이터가 없으면 샘플 데이터 반환
    if not results:
        results = [
            {
                "place_id": "sample-1",
                "place_name": "한강 공원 야경 피크닉",
                "description": "야경이 아름다운 한강 공원에서 돗자리 데이트",
                "category_name": "공원",
                "tags": ["야경", "피크닉", "야외", "무료"],
                "rating": 4.6,
                "coordinates": {"latitude": 37.528, "longitude": 126.932},
                "address": "서울 영등포구 여의동로",
                "phone": "",
            },
            {
                "place_id": "sample-2",
                "place_name": "조용한 북카페 힐링",
                "description": "내향 커플을 위한 아늑한 북카페",
                "category_name": "카페",
                "tags": ["카페", "실내", "힐링", "조용한"],
                "rating": 4.8,
                "coordinates": {"latitude": 37.560, "longitude": 126.975},
                "address": "서울 강남구",
                "phone": "",
            },
            {
                "place_id": "sample-3",
                "place_name": "낭만적인 루프탑 레스토랑",
                "description": "야경을 즐기며 식사할 수 있는 고급 레스토랑",
                "category_name": "레스토랑",
                "tags": ["레스토랑", "루프탑", "야경", "고급"],
                "rating": 4.7,
                "coordinates": {"latitude": 37.540, "longitude": 127.000},
                "address": "서울 강남구",
                "phone": "",
            },
        ]
    
    return results
