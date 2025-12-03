from __future__ import annotations

from collections import Counter
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from .challenges import get_progress
from .llm import generate_report_summary

VISITS_COL = "visits"
COUPLES_COL = "couples"
PLANS_COL = "plans"


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


async def build_monthly_report(db: AsyncIOMotorDatabase, couple_id: str, month: str, *, include_summary: bool = False) -> dict:
    """
    월별 리포트 생성
    
    데이터 출처: visits 컬렉션
    - visit_count: 해당 월의 visits 문서 개수 (created_at 기준)
    - top_tags: visits 문서의 tags 필드에서 가장 많이 나온 상위 3개 태그
    - emotion_stats: visits 문서의 emotion 필드에서 감정별 카운트
    - notes: visits 문서의 memo 필드 (LLM 요약 생성 시 사용)
    """
    start = datetime.fromisoformat(f"{month}-01")
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    # visits 컬렉션에서 해당 월의 방문 기록 조회 (created_at 기준)
    cursor = db[VISITS_COL].find(
        {
            "couple_id": ObjectId(couple_id),
            "created_at": {"$gte": start, "$lt": end},
        }
    )
    visit_count = 0
    tag_counter: Counter[str] = Counter()  # 태그별 카운트 (visits.tags 필드)
    emotion_counter: Counter[str] = Counter()  # 감정별 카운트 (visits.emotion 필드)
    notes = []  # 메모 수집 (visits.memo 필드)
    async for doc in cursor:
        visit_count += 1
        # visits 문서의 tags 필드에서 태그 수집
        for tag in doc.get("tags", []):
            tag_counter[tag] += 1
        # visits 문서의 emotion 필드에서 감정 수집
        emotion = doc.get("emotion")
        if emotion:
            emotion_counter[emotion] += 1
        # visits 문서의 memo 필드에서 메모 수집 (LLM 요약 생성 시 사용)
        memo = doc.get("memo")
        if memo:
            notes.append(memo)

    # 상위 3개 태그 추출 (인기 태그)
    top_tags = [tag for tag, _ in tag_counter.most_common(3)]
    # 감정별 통계 딕셔너리 (감정 분포)
    emotion_stats = dict(emotion_counter)
    challenges = await get_progress(db, couple_id)

    couple_doc = await db[COUPLES_COL].find_one({"_id": ObjectId(couple_id)}) or {}
    preferences = couple_doc.get("preferences", {})
    preferred_tags = preferences.get("tags", [])
    preferred_emotion_goals = preferences.get("emotion_goals", [])
    preferred_budget = preferences.get("budget", "medium")

    plan_cursor = db[PLANS_COL].find({"couple_id": ObjectId(couple_id)})
    plan_emotion_goals_set: set[str] = set()
    async for plan in plan_cursor:
        goal = plan.get("emotion_goal")
        if goal and goal != "미정":
            plan_emotion_goals_set.add(goal)
    plan_emotion_goals = sorted(plan_emotion_goals_set)

    summary_text = ""
    if include_summary:
        summary_text = await generate_report_summary(
            {
                "month": month,
                "visit_count": visit_count,
                "top_tags": top_tags,
                "emotion_stats": emotion_stats,
                "challenge_progress": challenges,  # 원래 challenges 리스트 사용
                "couple_preference_tags": preferred_tags,
                "couple_emotion_goals": preferred_emotion_goals,
                "couple_budget": preferred_budget,
                "plan_emotion_goals": plan_emotion_goals,
                "notes": "; ".join(notes[:5]),
            }
        )

    return {
        "month": month,
        "visit_count": visit_count,
        "top_tags": top_tags,
        "emotion_stats": emotion_stats,
        "challenge_progress": challenges,
        "preferred_tags": preferred_tags,
        "preferred_emotion_goals": preferred_emotion_goals,
        "preferred_budget": preferred_budget,
        "plan_emotion_goals": plan_emotion_goals,
        "summary": summary_text,
    }
