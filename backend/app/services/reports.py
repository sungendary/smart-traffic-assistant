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

    couple_doc = await db[COUPLES_COL].find_one({"_id": ObjectId(couple_id)}) or {}
    preferences = couple_doc.get("preferences", {})
    preferred_tags = preferences.get("tags", [])
    preferred_emotion_goals = preferences.get("emotion_goals", [])

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
                "challenge_progress": challenge_summary,
                "couple_preference_tags": preferred_tags,
                "couple_emotion_goals": preferred_emotion_goals,
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
        "plan_emotion_goals": plan_emotion_goals,
        "summary": summary_text,
    }
