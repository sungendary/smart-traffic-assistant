from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from google import genai

from ..core.config import settings


def _format_itinerary_prompt(emotion: str, preferences: str, location: str, additional_context: str) -> str:
    return f"""
당신은 연인을 위한 프리미엄 데이트 플래너입니다. 아래 정보를 참고하여 한국어로 세 가지 제안을 만듭니다.
- 감정 상태: {emotion}
- 선호 태그: {preferences}
- 지역 설명: {location}
- 추가 정보: {additional_context}

각 제안은 JSON 객체로 작성하세요. 형식은 아래와 같습니다.
[
  {{
    "title": "20자 이내 제목",
    "description": "두 문장 요약",
    "suggested_places": ["장소명 - 추천 이유", "...", "..."],
    "tips": ["팁1", "팁2"]
  }}
]
반드시 JSON 배열만 출력하세요.
"""


def _format_report_prompt(month: str, visit_count: int, top_tags: str, emotion_stats: str, challenge_progress: str, couple_preference_tags: list[str] = None, couple_emotion_goals: list[str] = None, plan_emotion_goals: list[str] = None, notes: str = "") -> str:
    pref_tags = ", ".join(couple_preference_tags or [])
    pref_emotions = ", ".join(couple_emotion_goals or [])
    plan_emotions = ", ".join(plan_emotion_goals or [])
    
    return f"""
당신은 귀여운 어린이 커플 매니저입니다. 아래 데이터를 보고 4~5문장으로 한국어 리포트를 작성하세요.
- 월: {month}
- 방문 횟수: {visit_count}
- 즐겨 찾은 태그 Top3: {top_tags}
- 감정 분포: {emotion_stats}
- 챌린지 진행도: {challenge_progress}
- 커플 선호 태그: {pref_tags or "없음"}
- 커플 감정 목표: {pref_emotions or "없음"}
- 플래너 감정 목표: {plan_emotions or "없음"}
- 추가 메모: {notes}

지켜야 할 규칙:
1. 유치원생이 들려주는 듯한 상냥하고 해맑은 톤을 유지하고, 이모지나 의성어를 1~2개 섞어도 좋습니다.
2. 커플이 좋아하는 태그/감정 목표/플래너 감정 목표를 꼭 한 번씩 언급하고, 통계 수치는 자연스럽게 녹여 주세요.
3. 어려운 전문 용어는 쓰지 말고, 마지막 문장은 두 사람이 다음 데이트를 응원하는 짧은 감탄사로 마무리하세요.
4. 중요한 단어나 구절은 **텍스트** 형식으로 강조해주세요 (예: **카페**, **식당**, **신나고 활발한**).
"""


@lru_cache
def get_gemini_client() -> genai.Client:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY를 추가하세요."
        )
    try:
        return genai.Client(api_key=settings.gemini_api_key)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Gemini 클라이언트 초기화 실패: {str(exc)}") from exc


async def _invoke_gemini(prompt: str) -> str:
    """Google Gemini API를 사용하여 프롬프트를 처리합니다."""
    client = get_gemini_client()
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=prompt,
        )
        if hasattr(response, "text"):
            return response.text
        elif hasattr(response, "candidates") and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, "content"):
                if hasattr(candidate.content, "parts"):
                    return "".join(part.text for part in candidate.content.parts if hasattr(part, "text"))
        return str(response)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API 호출 실패: {str(exc)}"
        ) from exc


async def generate_itinerary_suggestions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    emotion = payload.get("emotion", "")
    preferences = payload.get("preferences", "")
    location = payload.get("location", "")
    additional_context = payload.get("additional_context", "")
    
    prompt = _format_itinerary_prompt(emotion, preferences, location, additional_context)
    raw = await _invoke_gemini(prompt)
    
    # JSON 응답에서 코드 블록이나 마크다운 제거
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM 응답 파싱 실패: {str(exc)}, 원본 응답: {raw[:200]}") from exc

    if not isinstance(parsed, list):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM 응답 형식 오류")

    clean: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict):
            clean.append(
                {
                    "title": str(item.get("title", ""))[:40],
                    "description": str(item.get("description", "")),
                    "suggested_places": [str(p) for p in item.get("suggested_places", [])],
                    "tips": [str(t) for t in item.get("tips", [])],
                    "estimated_total_cost": item.get("estimated_total_cost", 0),
                }
            )
    return clean


async def generate_report_summary(payload: dict[str, Any]) -> str:
    month = payload.get("month", "")
    visit_count = payload.get("visit_count", 0)
    top_tags = ", ".join(payload.get("top_tags", []))
    emotion_stats = str(payload.get("emotion_stats", {}))
    challenge_progress = str(payload.get("challenge_progress", {}))
    couple_preference_tags = payload.get("couple_preference_tags", [])
    couple_emotion_goals = payload.get("couple_emotion_goals", [])
    plan_emotion_goals = payload.get("plan_emotion_goals", [])
    notes = payload.get("notes", "")
    
    prompt = _format_report_prompt(
        month, visit_count, top_tags, emotion_stats, challenge_progress,
        couple_preference_tags, couple_emotion_goals, plan_emotion_goals, notes
    )
    summary = await _invoke_gemini(prompt)
    return summary.strip()
