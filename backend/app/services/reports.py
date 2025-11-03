from __future__ import annotations

from collections import Counter
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from .challenges import get_progress
from fastapi import HTTPException

from .llm import generate_report_summary

VISITS_COL = "visits"
BOOKMARKS_COL = "bookmarks"


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


async def build_monthly_report(db: AsyncIOMotorDatabase, couple_id: str, month: str) -> dict:
    start = datetime.fromisoformat(f"{month}-01")
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    cursor = db[VISITS_COL].find(
        {
            "couple_id": ObjectId(couple_id),
            "created_at": {"$gte": start, "$lt": end},
        }
    )
    visit_count = 0
    tag_counter: Counter[str] = Counter()
    emotion_counter: Counter[str] = Counter()
    notes = []
    async for doc in cursor:
        visit_count += 1
        for tag in doc.get("tags", []):
            tag_counter[tag] += 1
        emotion = doc.get("emotion")
        if emotion:
            emotion_counter[emotion] += 1
        memo = doc.get("memo")
        if memo:
            notes.append(memo)

    top_tags = [tag for tag, _ in tag_counter.most_common(3)]
    emotion_stats = dict(emotion_counter)
    challenges = await get_progress(db, couple_id)
    challenge_summary = {c["id"]: c["completed"] for c in challenges}

    try:
        summary_text = await generate_report_summary(
            {
                "month": month,
                "visit_count": visit_count,
                "top_tags": top_tags,
                "emotion_stats": emotion_stats,
                "challenge_progress": challenge_summary,
                "notes": "; ".join(notes[:5]),
            }
        )
    except HTTPException as exc:  # LLM 호출 실패 시 기본 문구 사용
        summary_text = (
            f"{month} 리포트를 생성하는 동안 AI 요약을 불러오지 못했습니다. "
            "방문 기록과 감정 통계를 기반으로 직접 확인해 주세요."
        )

    return {
        "month": month,
        "visit_count": visit_count,
        "top_tags": top_tags,
        "emotion_stats": emotion_stats,
        "challenge_progress": challenges,
        "summary": summary_text,
    }
