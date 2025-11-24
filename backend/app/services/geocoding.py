"""지역명을 좌표로 변환하는 지오코딩 서비스"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


async def geocode_location_name(location_name: str) -> dict[str, Any] | None:
    """
    Kakao Local API를 사용해 지역명/장소명을 좌표로 변환
    
    Args:
        location_name: 변환할 지역명 (예: "강남역", "경기대", "광교역")
    
    Returns:
        {
            "lat": 37.497...,
            "lon": 127.027...,
            "name": "강남역",
            "address": "서울 강남구 강남대로"
        }
        또는 변환 실패 시 None
    """
    if not location_name:
        return None
    
    if not settings.kakao_rest_api_key:
        logger.warning("Kakao REST API 키가 설정되지 않음. 지역명 변환 불가")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # [수정됨] 주소 검색(address) 대신 키워드 검색(keyword) 사용
            # 이렇게 해야 "광교역", "경기대" 같은 장소명도 검색됩니다.
            response = await client.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json",
                params={"query": location_name, "size": 1},
                headers={"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Kakao API 오류: {response.status_code}")
                return None
            
            data = response.json()
            documents = data.get("documents", [])
            
            if not documents:
                logger.warning(f"지역명 '{location_name}' 검색 결과 없음")
                return None
            
            # 첫 번째 결과(가장 정확도 높은 것) 사용
            result = documents[0]
            
            return {
                "lat": float(result.get("y", 0)),
                "lon": float(result.get("x", 0)),
                "name": result.get("place_name", location_name),
                "address": result.get("road_address_name") or result.get("address_name", "")
            }
            
    except httpx.HTTPError as e:
        logger.error(f"Kakao API 호출 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"지역명 변환 중 오류: {e}")
        return None


async def get_coordinates_from_location(location_desc: str, fallback_lat: float = 37.5665, fallback_lon: float = 126.9780) -> tuple[float, float]:
    """
    지역명에서 좌표를 추출하거나, 없으면 기본값 반환
    """
    if not location_desc:
        return fallback_lat, fallback_lon
    
    # 이미 좌표 형식인 경우 (예: "37.123,126.456")
    if "," in location_desc:
        try:
            parts = location_desc.split(",")
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                return lat, lon
        except (ValueError, IndexError):
            pass
    
    # 지역명으로부터 좌표 추출 시도
    result = await geocode_location_name(location_desc)
    if result:
        return result["lat"], result["lon"]
    
    # 실패 시 기본값 반환
    return fallback_lat, fallback_lon