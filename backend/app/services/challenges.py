from __future__ import annotations

from collections import Counter
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

VISITS_COL = "visits"

CHALLENGE_DEFINITIONS = [
    {
        "id": "night_explorer",
        "title": "밤의 탐험가",
        "description": "야경 태그 장소 3곳 방문",
        "criteria": {"tag": "야경", "count": 3},
        "badge_icon": "🌃",
    },
    {
        "id": "coffee_holic",
        "title": "카페 매니아",
        "description": "카페 태그 장소 5곳 방문",
        "criteria": {"tag": "카페", "count": 5},
        "badge_icon": "☕",
    },
    {
        "id": "healing_master",
        "title": "힐링 마스터",
        "description": "감정 '힐링' 리뷰 4회 이상",
        "criteria": {"emotion": "힐링", "count": 4},
        "badge_icon": "🌿",
    },
]


async def get_progress(db: AsyncIOMotorDatabase, couple_id: str) -> list[dict]:
    cursor = db[VISITS_COL].find({"couple_id": ObjectId(couple_id)})
    tag_counter: Counter[str] = Counter()
    emotion_counter: Counter[str] = Counter()
    async for doc in cursor:
        for tag in doc.get("tags", []):
            tag_counter[tag] += 1
        emotion = doc.get("emotion")
        if emotion:
            emotion_counter[emotion] += 1

    progress: list[dict] = []
    for challenge in CHALLENGE_DEFINITIONS:
        criteria = challenge["criteria"]
        if "tag" in criteria:
            current = tag_counter[criteria["tag"]]
        else:
            current = emotion_counter[criteria["emotion"]]
        done = current >= criteria["count"]
        progress.append(
            {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "badge_icon": challenge["badge_icon"],
                "current": current,
                "goal": criteria["count"],
                "completed": done,
                "completed_at": datetime.utcnow().isoformat() if done else None,
            }
        )
    return progress
