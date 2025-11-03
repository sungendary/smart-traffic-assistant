from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .llm_tasks import LLMTaskType, enqueue_llm_task
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
) -> dict[str, Any]:
    places = await list_places(db, latitude=latitude, longitude=longitude, tags=preferences or None, limit=6)
    if not places:
        places = FALLBACK_PLACES

    task_id = await enqueue_llm_task(
        LLMTaskType.ITINERARY,
        {
            "emotion": emotion,
            "preferences": ", ".join(preferences) or "없음",
            "location": location_text,
            "additional_context": additional_context or "",
        },
    )

    return {
        "summary": f"{emotion} 상태에 맞춘 맞춤 추천을 구성했습니다.",
        "places": [place.model_dump() for place in places],
        "llm_suggestions": [],
        "llm_task_id": task_id,
        "llm_status": "pending",
    }
