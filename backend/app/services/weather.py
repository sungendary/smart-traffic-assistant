"""날씨 정보 조회 서비스 (OpenWeatherMap API)"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, status

from ..core.config import settings

logger = logging.getLogger(__name__)

WEATHER_CACHE_TTL = 1800  # 30분 캐시


class WeatherCondition:
    """날씨 상태 분류"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"


async def get_weather_info(lat: float, lon: float, redis_client=None) -> dict[str, Any]:
    """
    OpenWeatherMap API를 사용하여 현재 날씨 정보 조회
    
    Args:
        lat: 위도
        lon: 경도
        redis_client: Redis 캐시 (선택)
    
    Returns:
        {
            "condition": "sunny" | "cloudy" | "rainy" | "snowy" | "stormy",
            "temperature": 15.5,
            "humidity": 60,
            "description": "맑음",
            "icon": "01d"
        }
    """
    if not settings.openweather_api_key:
        logger.warning("OpenWeatherMap API 키가 설정되지 않음. 기본 날씨 반환")
        return _get_default_weather()
    
    # Redis 캐시 확인
    cache_key = f"weather:{lat:.2f}:{lon:.2f}"
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis 캐시 조회 실패: {e}")
    
    # API 호출
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                    "lang": "kr"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            weather_info = _parse_weather_response(data)
            
            # Redis 캐싱
            if redis_client:
                try:
                    import json
                    await redis_client.setex(
                        cache_key,
                        WEATHER_CACHE_TTL,
                        json.dumps(weather_info)
                    )
                except Exception as e:
                    logger.warning(f"Redis 캐싱 실패: {e}")
            
            return weather_info
            
    except httpx.HTTPStatusError as e:
        logger.error(f"날씨 API 호출 실패: {e}")
        return _get_default_weather()
    except Exception as e:
        logger.error(f"날씨 조회 중 오류: {e}")
        return _get_default_weather()


def _parse_weather_response(data: dict) -> dict[str, Any]:
    """OpenWeatherMap API 응답 파싱"""
    weather_main = data.get("weather", [{}])[0]
    main_data = data.get("main", {})
    
    # 날씨 코드에 따른 상태 분류
    weather_id = weather_main.get("id", 800)
    condition = _classify_weather_condition(weather_id)
    
    return {
        "condition": condition,
        "temperature": round(main_data.get("temp", 15.0), 1),
        "feels_like": round(main_data.get("feels_like", 15.0), 1),
        "humidity": main_data.get("humidity", 60),
        "description": weather_main.get("description", "알 수 없음"),
        "icon": weather_main.get("icon", "01d"),
        "wind_speed": data.get("wind", {}).get("speed", 0)
    }


def _classify_weather_condition(weather_id: int) -> str:
    """날씨 코드를 카테고리로 분류"""
    if weather_id == 800:  # Clear
        return WeatherCondition.SUNNY
    elif 200 <= weather_id < 300:  # Thunderstorm
        return WeatherCondition.STORMY
    elif 300 <= weather_id < 600:  # Drizzle, Rain
        return WeatherCondition.RAINY
    elif 600 <= weather_id < 700:  # Snow
        return WeatherCondition.SNOWY
    elif 801 <= weather_id < 900:  # Clouds
        return WeatherCondition.CLOUDY
    else:
        return WeatherCondition.CLOUDY


def _get_default_weather() -> dict[str, Any]:
    """기본 날씨 정보 (API 실패 시)"""
    return {
        "condition": WeatherCondition.SUNNY,
        "temperature": 20.0,
        "feels_like": 20.0,
        "humidity": 60,
        "description": "날씨 정보를 가져올 수 없습니다",
        "icon": "01d",
        "wind_speed": 0
    }


def get_weather_based_suggestions(condition: str) -> dict[str, Any]:
    """날씨에 따른 추천 활동 및 주의사항"""
    suggestions = {
        WeatherCondition.SUNNY: {
            "recommended_activities": ["야외 산책", "공원 피크닉", "한강 자전거", "루프탑 카페", "전망대"],
            "place_types": ["park", "cafe_outdoor", "river", "mountain", "rooftop"],
            "tips": ["자외선 차단제 필수", "시원한 음료 준비", "모자나 선글라스 착용"],
            "avoid": []
        },
        WeatherCondition.CLOUDY: {
            "recommended_activities": ["미술관", "박물관", "실내외 겸용 카페", "쇼핑", "드라이브"],
            "place_types": ["museum", "gallery", "cafe", "shopping", "drive"],
            "tips": ["언제든 비가 올 수 있으니 우산 챙기기"],
            "avoid": []
        },
        WeatherCondition.RAINY: {
            "recommended_activities": ["실내 카페", "영화관", "찜질방", "실내 데이트", "맛집 투어"],
            "place_types": ["cafe_indoor", "movie", "spa", "restaurant", "indoor"],
            "tips": ["우산과 여벌 옷 준비", "따뜻한 음료 추천", "감성적인 분위기 즐기기"],
            "avoid": ["야외 활동", "산책", "공원"]
        },
        WeatherCondition.SNOWY: {
            "recommended_activities": ["눈 구경 산책", "따뜻한 실내 카페", "온천/찜질방", "겨울 축제"],
            "place_types": ["cafe_warm", "spa", "indoor", "winter_festival"],
            "tips": ["따뜻한 옷 챙기기", "미끄럼 주의", "핫초코 추천"],
            "avoid": ["먼 거리 이동", "야외 장시간 활동"]
        },
        WeatherCondition.STORMY: {
            "recommended_activities": ["실내 데이트", "홈 데이트", "근처 카페", "영화 감상"],
            "place_types": ["cafe_indoor", "movie", "indoor", "home"],
            "tips": ["외출 자제 권장", "안전한 실내 활동 추천"],
            "avoid": ["모든 야외 활동", "먼 거리 이동"]
        }
    }
    
    return suggestions.get(condition, suggestions[WeatherCondition.CLOUDY])
