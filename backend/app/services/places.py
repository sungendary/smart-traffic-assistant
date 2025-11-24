import logging
import httpx
from typing import Iterable, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.config import settings
from ..schemas.place import Place

logger = logging.getLogger(__name__)

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


async def search_places_via_kakao(
    lat: float,
    lon: float,
    radius_m: int = 5000,
    limit: int = 15
) -> list[dict[str, Any]]:
    """
    Kakao Local API를 사용하여 주변 장소 검색 (카테고리별)
    """
    if not settings.kakao_rest_api_key:
        return []

    # 데이트에 적합한 카테고리 코드
    # FD6: 음식점, CE7: 카페, CT1: 문화시설, AT4: 관광명소
    categories = ["FD6", "CE7", "CT1", "AT4"]
    all_results = []
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for code in categories:
            try:
                response = await client.get(
                    "https://dapi.kakao.com/v2/local/search/category.json",
                    params={
                        "category_group_code": code,
                        "x": lon,
                        "y": lat,
                        "radius": radius_m,
                        "sort": "distance",
                        "size": 5  # 카테고리별 5개씩
                    },
                    headers={"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    documents = data.get("documents", [])
                    
                    for doc in documents:
                        # 카테고리 이름 파싱 (예: "음식점 > 카페 > 테마카페")
                        cat_name = doc.get("category_name", "").split(">")[-1].strip()
                        if not cat_name:
                            cat_name = doc.get("category_group_name", "기타")
                              # 태그 생성
                        tags = [cat_name]
                        if code == "FD6":
                            tags.append("맛집")
                        elif code == "CE7":
                            tags.append("카페")
                        elif code == "CT1":
                            tags.append("문화")
                        elif code == "AT4":
                            tags.append("관광")
                        
                        place = {
                            "place_id": f"kakao-{doc.get('id')}",
                            "place_name": doc.get("place_name"),
                            "description": f"{doc.get('place_name')} - {cat_name}",
                            "category_name": cat_name,
                            "tags": tags,
                            "rating": 0.0, # Kakao API는 평점 미제공
                            "coordinates": {
                                "latitude": float(doc.get("y")),
                                "longitude": float(doc.get("x"))
                            },
                            "address": doc.get("road_address_name") or doc.get("address_name"),
                            "phone": doc.get("phone", ""),
                            "place_url": doc.get("place_url"),
                            "source": "kakao"
                        }
                        all_results.append(place)
            except Exception as e:
                logger.warning(f"Kakao API 카테고리 {code} 검색 실패: {e}")
                continue
                
    return all_results


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
    DB에 데이터가 부족하면 Kakao API를 통해 보충
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
            "source": "db"
        }
        results.append(place_dict)
    
    # DB 결과가 부족하고 Kakao API 키가 있으면 외부 API 호출
    if len(results) < 5 and settings.kakao_rest_api_key:
        try:
            kakao_places = await search_places_via_kakao(lat, lon, int(radius_km * 1000))
            # 중복 제거 (이름 기준)
            existing_names = {p["place_name"] for p in results}
            for kp in kakao_places:
                if kp["place_name"] not in existing_names:
                    results.append(kp)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"Kakao 장소 검색 실패: {e}")

    # 여전히 데이터가 없으면 샘플 데이터 반환
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
                "source": "sample"
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
                "source": "sample"
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
                "source": "sample"
            },
        ]
    
    return results
