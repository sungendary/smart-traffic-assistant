"""
위치 계산 유틸리티 함수
Haversine 공식을 사용하여 두 좌표 간의 거리를 계산합니다.
"""

import math


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine 공식을 사용하여 두 지점 간의 거리를 계산합니다.
    
    Args:
        lat1: 첫 번째 지점의 위도
        lon1: 첫 번째 지점의 경도
        lat2: 두 번째 지점의 위도
        lon2: 두 번째 지점의 경도
    
    Returns:
        두 지점 간의 거리 (미터 단위)
    """
    # 지구 반경 (미터)
    R = 6371000
    
    # 라디안으로 변환
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine 공식
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def is_within_radius(
    user_lat: float, user_lon: float, place_lat: float, place_lon: float, radius_meters: float = 1000
) -> bool:
    """
    사용자 위치가 지정된 반경 내에 있는지 확인합니다.
    
    Args:
        user_lat: 사용자 위치의 위도
        user_lon: 사용자 위치의 경도
        place_lat: 장소의 위도
        place_lon: 장소의 경도
        radius_meters: 반경 (미터 단위, 기본값 1000m = 1km)
    
    Returns:
        반경 내에 있으면 True, 그렇지 않으면 False
    """
    distance = calculate_distance(user_lat, user_lon, place_lat, place_lon)
    return distance <= radius_meters





