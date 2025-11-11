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
<<<<<<< Updated upstream
    - 예산 범위: {budget}
    - 날짜 및 날씨: {date} ({weather})
=======
    - 현재 날씨: {weather}
    - 예산 범위: {budget}
>>>>>>> Stashed changes
    - 추가 정보: {additional_context}

    날씨와 예산을 고려하여 실용적이고 현실적인 추천을 제공하세요.
    예를 들어, 비가 오면 실내 활동을 추천하고, 예산이 낮으면 무료/저렴한 장소를 우선 제안하세요.

    각 제안은 JSON 객체로 작성하세요. 형식은 아래와 같습니다.
    [
      {{
        "title": "20자 이내 제목 (예산/날씨 고려)",
        "description": "두 문장 요약 (예산과 날씨가 어떻게 반영되었는지 언급)",
        "suggested_places": ["장소명 - 추천 이유", "...", "..."],
        "tips": ["팁1", "팁2"],
        "estimated_total_cost": "예상 총 비용 (숫자만)"
      }}
    ]
    반드시 JSON 배열만 출력하세요.
    """
)

REPORT_PROMPT = ChatPromptTemplate.from_template(
    """
    당신은 커플 관계 인사이트 분석가입니다. 다음 데이터를 참고하여 4~5문장으로 한국어 요약을 작성하세요.
    - 월: {month}
    - 방문 횟수: {visit_count}
    - 즐겨 찾은 태그 Top3: {top_tags}
    - 감정 분포: {emotion_stats}
    - 챌린지 진행도: {challenge_progress}
    - 추가 메모: {notes}

    항목 번호 없이 자연스러운 문단으로 작성하고, 긍정적인 제안 1가지를 마지막에 포함하세요.
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
                    "estimated_total_cost": item.get("estimated_total_cost", 0),
                }
            )
    return clean


async def generate_report_summary(payload: dict[str, Any]) -> str:
    summary = await _invoke(REPORT_PROMPT, payload)
    return summary.strip()
