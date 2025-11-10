from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from ..core.config import settings

ITINERARY_PROMPT = ChatPromptTemplate.from_template(
    """
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
)

REPORT_PROMPT = ChatPromptTemplate.from_template(
    """
    당신은 귀여운 어린이 커플 매니저 "토토"입니다. 아래 데이터를 보고 4~5문장으로 한국어 리포트를 작성하세요.
    - 월: {month}
    - 방문 횟수: {visit_count}
    - 즐겨 찾은 태그 Top3: {top_tags}
    - 감정 분포: {emotion_stats}
    - 챌린지 진행도: {challenge_progress}
    - 커플 선호 태그: {couple_preference_tags}
    - 커플 감정 목표: {couple_emotion_goals}
    - 플래너 감정 목표: {plan_emotion_goals}
    - 추가 메모: {notes}

    지켜야 할 규칙:
    1. 유치원생이 들려주는 듯한 상냥하고 해맑은 톤을 유지하고, 이모지나 의성어를 1~2개 섞어도 좋습니다.
    2. 커플이 좋아하는 태그/감정 목표/플래너 감정 목표를 꼭 한 번씩 언급하고, 통계 수치는 자연스럽게 녹여 주세요.
    3. 어려운 전문 용어는 쓰지 말고, 마지막 문장은 두 사람이 다음 데이트를 응원하는 짧은 감탄사로 마무리하세요.
    """
)


@lru_cache
def get_llm() -> ChatOllama:
    try:
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


async def _invoke(prompt_template: ChatPromptTemplate, kwargs: dict[str, Any]) -> str:
    llm = get_llm()
    chain = prompt_template | llm
    try:
        response = await chain.ainvoke(kwargs)
    except AttributeError:
        response = await asyncio.to_thread(chain.invoke, kwargs)
    content = getattr(response, "content", None)
    if not isinstance(content, str):
        content = str(response)
    return content


async def generate_itinerary_suggestions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = await _invoke(ITINERARY_PROMPT, payload)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM 응답 파싱 실패") from exc

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
                }
            )
    return clean


async def generate_report_summary(payload: dict[str, Any]) -> str:
    summary = await _invoke(REPORT_PROMPT, payload)
    return summary.strip()
