from typing import Iterable

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.place import Place

PLACES_COLLECTION = "places"

FALLBACK_PLACES: list[Place] = [
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
    latitude: float | None = None,
    longitude: float | None = None,
    tags: Iterable[str] | None = None,
    limit: int = 10,
) -> list[Place]:
    collection = db[PLACES_COLLECTION]
    query: dict = {}

    if tags:
        query["tags"] = {"$in": list(tags)}

    if latitude is not None and longitude is not None:
        query["location"] = {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "$maxDistance": 5_000,
            }
        }

    cursor = collection.find(query).limit(limit)
    results: list[Place] = []
    async for doc in cursor:
        results.append(Place.from_mongo(doc))

    if results:
        return results

    return FALLBACK_PLACES[: limit if limit > 0 else None]


async def insert_sample_place(db: AsyncIOMotorDatabase, place: Place) -> str:
    collection = db[PLACES_COLLECTION]
    payload = {
        "name": place.name,
        "description": place.description,
        "location": {"type": "Point", "coordinates": [place.coordinates.longitude, place.coordinates.latitude]},
        "tags": place.tags,
        "rating": place.rating,
        "source": place.source,
    }
    result = await collection.insert_one(payload)
    return str(result.inserted_id)
