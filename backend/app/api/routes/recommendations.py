"""스마트 데이트 코스 추천 API"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db, get_redis_client
from ...schemas.user import UserPublic
from ...services.geocoding import get_coordinates_from_location
from ...services.llm import generate_itinerary_suggestions
from ...services.recommendations import (
    filter_by_budget,
    get_budget_label,
    rank_places_by_score,
)
from ...services.weather import get_weather_info, get_weather_based_suggestions

router = APIRouter()


@router.post("/recommend")
async def get_smart_recommendations(
    lat: float = Query(default=37.5665, description="위도 (location_desc가 있으면 무시됨)"),
    lon: float = Query(default=126.9780, description="경도 (location_desc가 있으면 무시됨)"),
    preferences: list[str] = Query(default=[], description="취향 태그 (예: romantic, food, outdoor)"),
    budget_range: str = Query(default="medium", description="예산 범위: free/low/medium/high/premium"),
    emotion: str = Query(default="", description="감정 상태 (선택)"),
    location_desc: str = Query(default="", description="🔴 중요: 지역 설명 (예: '광교역', '강남역', '수원') - 입력 필수!"),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    redis=Depends(get_redis_client),
) -> dict[str, Any]:
    """
    취향, 예산, 날씨를 고려한 스마트 데이트 코스 추천
    
    🔴 반드시 location_desc 파라미터에 지역명을 입력하세요!
    
    - location_desc 기반 좌표 자동 변환
    - 현재 위치의 날씨 정보 조회
    - 날씨에 적합한 활동 제안
    - 예산 범위 내 장소 필터링
    - 취향 기반 개인화 추천
    - AI 기반 코스 제안
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 지역명이 입력된 경우, 지역명을 좌표로 변환
    original_lat, original_lon = lat, lon
    if location_desc:
        logger.info(f"📍 지역명 변환 시작: '{location_desc}'")
        lat, lon = await get_coordinates_from_location(location_desc, fallback_lat=lat, fallback_lon=lon)
        logger.info(f"📍 변환 결과: {location_desc} → ({lat}, {lon})")
        
        # 변환 전후 좌표 비교로 실제 변환 확인
        if (lat, lon) != (original_lat, original_lon):
            logger.info(f"✅ 지역명 변환 성공: ({original_lat}, {original_lon}) → ({lat}, {lon})")
        else:
            logger.warning(f"⚠️ 지역명 변환 실패 또는 기본값 사용: {location_desc}")
    else:
        logger.warning("⚠️ location_desc 파라미터가 비어있음 - 기본 위치(서울) 사용")
    
    # 1. 날씨 정보 조회
    weather_info = await get_weather_info(lat, lon, redis)
    weather_suggestions = get_weather_based_suggestions(weather_info["condition"])
    
    # 2. 주변 장소 조회 (기존 places 서비스 활용)
    from ...services.places import get_nearby_places
    
    nearby_places = await get_nearby_places(
        db=db,
        lat=lat,
        lon=lon,
        radius_km=5.0,
        limit=50
    )
    
    # 3. 예산 필터링
    budget_filtered = filter_by_budget(nearby_places, budget_range)
    
    # 4. 종합 점수로 랭킹
    ranked_places = rank_places_by_score(
        places=budget_filtered,
        preferences=preferences,
        weather_condition=weather_info["condition"],
        budget_range=budget_range
    )
    
    # 상위 10개 선택
    top_places = ranked_places[:10]
    
    # 5. AI 기반 코스 제안 생성
    weather_description = f"{weather_info['description']} (기온: {weather_info['temperature']}°C)"
    budget_label = get_budget_label(budget_range)
    
    llm_payload = {
        "emotion": emotion or "평온한",
        "preferences": ", ".join(preferences) if preferences else "다양한 경험",
        "location": location_desc or f"위도 {lat:.2f}, 경도 {lon:.2f}",
        "weather": weather_description,
        "budget": budget_label,
        "additional_context": f"추천 장소: {', '.join([p.get('place_name', '') for p in top_places[:5]])}"
    }
    
    try:
        ai_suggestions = await generate_itinerary_suggestions(llm_payload)
    except Exception as e:
        # AI 실패 시 기본 제안
        ai_suggestions = [
            {
                "title": "주변 추천 코스",
                "description": "선택하신 조건에 맞는 장소들을 찾았습니다.",
                "suggested_places": [p.get("place_name", "") for p in top_places[:3]],
                "tips": weather_suggestions["tips"],
                "estimated_total_cost": 0
            }
        ]
    
    # 6. 응답 구성
    return {
        "weather": weather_info,
        "weather_suggestions": {
            "recommended_activities": weather_suggestions["recommended_activities"],
            "tips": weather_suggestions["tips"],
            "avoid": weather_suggestions.get("avoid", [])
        },
        "budget_info": {
            "range": budget_range,
            "label": budget_label,
            "description": f"1인 기준 {budget_label} 내 장소를 추천합니다"
        },
        "recommended_places": top_places,
        "ai_course_suggestions": ai_suggestions,
        "summary": {
            "total_places_found": len(nearby_places),
            "after_filtering": len(budget_filtered),
            "top_recommendations": len(top_places)
        }
    }


@router.get("/weather")
async def get_current_weather(
    lat: float = Query(..., description="위도"),
    lon: float = Query(..., description="경도"),
    current_user: UserPublic = Depends(get_current_user),
    redis=Depends(get_redis_client),
) -> dict[str, Any]:
    """현재 위치의 날씨 정보 조회"""
    weather_info = await get_weather_info(lat, lon, redis)
    suggestions = get_weather_based_suggestions(weather_info["condition"])
    
    return {
        "weather": weather_info,
        "suggestions": suggestions
    }


@router.get("/budget-ranges")
async def get_budget_ranges(
    current_user: UserPublic = Depends(get_current_user),
) -> dict[str, Any]:
    """예산 범위 옵션 조회"""
    from ...services.recommendations import BUDGET_RANGES
    
    return {
        "ranges": [
            {
                "key": key,
                "label": info["label"],
                "min": info["min"],
                "max": info["max"]
            }
            for key, info in BUDGET_RANGES.items()
        ]
    }


@router.get("/preference-tags")
async def get_preference_tags(
    current_user: UserPublic = Depends(get_current_user),
) -> dict[str, Any]:
    """사용 가능한 취향 태그 목록 조회"""
    from ...services.recommendations import PREFERENCE_TAGS
    
    categories = {
        "emotion": ["romantic", "energetic", "relaxing", "adventurous", "cultural"],
        "activity": ["food", "nature", "indoor", "outdoor", "creative"],
        "mood": ["quiet", "lively", "trendy", "classic"]
    }
    
    tags_with_keywords = {}
    for key, keywords in PREFERENCE_TAGS.items():
        tags_with_keywords[key] = {
            "keywords": keywords,
            "label": key.replace("_", " ").title()
        }
    
    return {
        "categories": categories,
        "tags": tags_with_keywords
    }
