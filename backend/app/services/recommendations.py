"""취향 및 예산 기반 장소 필터링 및 추천 로직"""
from __future__ import annotations

import random

# 예산 범위 정의 (원 단위)
BUDGET_RANGES = {
    "free": {"min": 0, "max": 0, "label": "무료"},
    "low": {"min": 0, "max": 30000, "label": "3만원 이하"},
    "medium": {"min": 30000, "max": 80000, "label": "3~8만원"},
    "high": {"min": 80000, "max": 150000, "label": "8~15만원"},
    "premium": {"min": 150000, "max": 999999, "label": "15만원 이상"}
}

# 취향(감정/활동) 태그 정의
PREFERENCE_TAGS = {
    # 감정 기반
    "romantic": ["낭만적인", "로맨틱", "감성", "분위기"],
    "energetic": ["활동적인", "액티비티", "스포츠", "체험"],
    "relaxing": ["편안한", "힐링", "조용한", "여유"],
    "adventurous": ["모험적인", "새로운", "특별한", "독특한"],
    "cultural": ["문화적인", "예술", "전시", "공연"],
    
    # 활동 타입
    "food": ["맛집", "카페", "디저트", "레스토랑", "음식"],
    "nature": ["자연", "공원", "산", "바다", "숲"],
    "indoor": ["실내", "쇼핑", "전시", "영화"],
    "outdoor": ["야외", "산책", "피크닉", "캠핑"],
    "creative": ["체험", "공방", "만들기", "창작"],
    
    # 분위기
    "quiet": ["조용한", "한적한", "프라이빗"],
    "lively": ["활기찬", "북적이는", "번화가"],
    "trendy": ["트렌디", "핫플", "인스타", "유명한"],
    "classic": ["전통적인", "클래식", "고급스러운"]
}

# 장소 카테고리별 평균 예산 추정
PLACE_BUDGET_ESTIMATE = {
    "cafe": {"avg": 15000, "range": "low"},
    "restaurant": {"avg": 40000, "range": "medium"},
    "fine_dining": {"avg": 120000, "range": "high"},
    "park": {"avg": 0, "range": "free"},
    "museum": {"avg": 10000, "range": "low"},
    "movie": {"avg": 30000, "range": "low"},
    "spa": {"avg": 50000, "range": "medium"},
    "activity": {"avg": 60000, "range": "medium"},
    "shopping": {"avg": 80000, "range": "high"},
    "bar": {"avg": 50000, "range": "medium"},
    "rooftop": {"avg": 70000, "range": "high"},
    "exhibition": {"avg": 20000, "range": "low"},
    "performance": {"avg": 80000, "range": "high"},
}


def match_preference_score(place: dict, preferences: list[str]) -> float:
    """
    장소와 취향 선호도 매칭 점수 계산
    
    Args:
        place: 장소 정보 (tags, category, description 등)
        preferences: 사용자 선호 태그 리스트
    
    Returns:
        0.0 ~ 1.0 점수
    """
    if not preferences:
        return 0.5  # 중립
    
    place_tags = set(place.get("tags", []))
    place_name = place.get("place_name", "").lower()
    place_category = place.get("category_name", "").lower()
    
    score = 0.0
    max_score = len(preferences)
    
    for pref in preferences:
        pref_keywords = PREFERENCE_TAGS.get(pref, [pref])
        
        for keyword in pref_keywords:
            keyword_lower = keyword.lower()
            # 태그 매칭
            if keyword_lower in [tag.lower() for tag in place_tags]:
                score += 1.0
                break
            # 이름 매칭
            elif keyword_lower in place_name:
                score += 0.8
                break
            # 카테고리 매칭
            elif keyword_lower in place_category:
                score += 0.6
                break
    
    return min(score / max_score, 1.0) if max_score > 0 else 0.5


def filter_by_budget(places: list[dict], budget_range: str) -> list[dict]:
    """
    예산 범위에 맞는 장소 필터링
    
    Args:
        places: 장소 리스트
        budget_range: "free", "low", "medium", "high", "premium"
    
    Returns:
        필터링된 장소 리스트
    """
    if budget_range not in BUDGET_RANGES:
        return places
    
    budget_info = BUDGET_RANGES[budget_range]
    budget_min = budget_info["min"]
    budget_max = budget_info["max"]
    
    filtered = []
    for place in places:
        place_budget = estimate_place_budget(place)
        
        if budget_min <= place_budget <= budget_max:
            filtered.append(place)
        # 예산 정보가 없는 경우, 카테고리 기반 추정
        elif place_budget == 0:
            category = place.get("category_name", "").lower()
            estimated_range = _estimate_category_budget_range(category)
            if estimated_range == budget_range or budget_range == "premium":
                filtered.append(place)
    
    return filtered


def estimate_place_budget(place: dict) -> int:
    """
    장소의 예상 예산 추정
    
    Args:
        place: 장소 정보
    
    Returns:
        예상 비용 (원)
    """
    # 명시적 예산 정보가 있으면 사용
    if "estimated_cost" in place:
        return place["estimated_cost"]
    
    # 카테고리 기반 추정
    category = place.get("category_name", "").lower()
    
    for key, info in PLACE_BUDGET_ESTIMATE.items():
        if key in category:
            return info["avg"]
    
    # 태그 기반 추정
    tags = place.get("tags", [])
    if "고급" in tags or "프리미엄" in tags:
        return 100000
    elif "저렴" in tags or "가성비" in tags:
        return 20000
    
    return 40000  # 기본값


def _estimate_category_budget_range(category: str) -> str:
    """카테고리로 예산 범위 추정"""
    for key, info in PLACE_BUDGET_ESTIMATE.items():
        if key in category:
            return info["range"]
    return "medium"


def rank_places_by_score(
    places: list[dict],
    preferences: list[str],
    weather_condition: str,
    budget_range: str
) -> list[dict]:
    """
    종합 점수로 장소 순위 매기기
    
    Args:
        places: 장소 리스트
        preferences: 선호 태그
        weather_condition: 날씨 상태
        budget_range: 예산 범위
    
    Returns:
        점수순 정렬된 장소 리스트 (각 장소에 score 필드 추가)
    """
    from .weather import get_weather_based_suggestions
    
    weather_suggestions = get_weather_based_suggestions(weather_condition)
    weather_types = set(weather_suggestions["place_types"])
    avoid_types = set(weather_suggestions.get("avoid", []))
    
    scored_places = []
    
    for place in places:
        # 1. 선호도 점수 (0~1)
        pref_score = match_preference_score(place, preferences)
        
        # 2. 날씨 적합도 점수 (0~1)
        weather_score = 0.5
        place_type = place.get("place_type", "").lower()
        place_category = place.get("category_name", "").lower()
        
        # 날씨에 추천되는 타입이면 가산점
        for wtype in weather_types:
            if wtype in place_type or wtype in place_category:
                weather_score = 1.0
                break
        
        # 날씨에 피해야 할 타입이면 감점
        for avoid in avoid_types:
            if avoid in place_type or avoid in place_category:
                weather_score = 0.1
                break
        
        # 3. 예산 적합도 (0~1)
        budget_score = 1.0
        place_budget = estimate_place_budget(place)
        budget_info = BUDGET_RANGES.get(budget_range, BUDGET_RANGES["medium"])
        
        if budget_info["min"] <= place_budget <= budget_info["max"]:
            budget_score = 1.0
        elif place_budget > budget_info["max"]:
            # 예산 초과시 점수 감소
            budget_score = max(0.3, 1.0 - (place_budget - budget_info["max"]) / budget_info["max"])
        
        # 4. 최종 점수 (가중 평균) + 약간의 랜덤성 (0.0~0.05)
        # 랜덤성을 추가하여 매번 조금씩 다른 순서를 제공
        random_factor = random.random() * 0.05
        
        final_score = (
            pref_score * 0.4 +
            weather_score * 0.35 +
            budget_score * 0.25 +
            random_factor
        )
        
        place_copy = {**place}
        place_copy["recommendation_score"] = round(final_score, 3)
        place_copy["estimated_cost"] = place_budget
        scored_places.append(place_copy)
    
    # 점수순 정렬
    scored_places.sort(key=lambda x: x["recommendation_score"], reverse=True)
    
    return scored_places


def get_budget_label(budget_range: str) -> str:
    """예산 범위의 한글 레이블 반환"""
    return BUDGET_RANGES.get(budget_range, {}).get("label", "알 수 없음")
