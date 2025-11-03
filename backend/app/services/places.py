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
