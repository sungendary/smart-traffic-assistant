from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .llm import generate_itinerary_suggestions
from .places import FALLBACK_PLACES, list_places


async def get_map_suggestions(
    db: AsyncIOMotorDatabase,
    *,
    latitude: float,
    longitude: float,
    emotion: str,
    preferences: list[str],
    location_text: str,
    additional_context: str | None = None,
    budget: str | None = None,
    date: date | None = None,
) -> dict[str, Any]:
    places = await list_places(db, latitude=latitude, longitude=longitude, tags=preferences or None, limit=6)
    if not places:
        places = FALLBACK_PLACES
    weather_info = "정보 없음"
    # if date:
    #      weather_info = await get_weather(latitude, longitude, date)

    suggestions = await generate_itinerary_suggestions(
        {
            "emotion": emotion,
            "preferences": ", ".join(preferences) or "없음",
            "location": location_text,
            "weather": "날씨 정보 없음",  # 기본값
            "budget": "제한 없음",  # 기본값
            "additional_context": additional_context or "",
            "budget": budget or "정보 없음",
            "date": str(date) if date else "정보 없음",
            "weather": weather_info,
        }
    )

    return {
        "summary": f"{emotion} 상태에 맞춘 맞춤 추천을 구성했습니다.",
        "places": [place.model_dump() for place in places],
        "llm_suggestions": suggestions,
    }
