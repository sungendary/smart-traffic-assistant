from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.app.services import llm


@pytest.fixture
def itinerary_payload() -> dict[str, Any]:
    return {
        "emotion": "설렘",
        "preferences": "카페, 야경",
        "location": "서울 홍대입구역 인근",
        "additional_context": "기념일이어서 특별한 무드를 원해요",
    }


@pytest.mark.contract
def test_itinerary_prompt_contract(monkeypatch: pytest.MonkeyPatch, itinerary_payload: dict[str, Any]) -> None:
    sample_response = """
    [
      {
        "title": "야경과 재즈",
        "description": "낭만적인 밤을 위한 두 가지 루트",
        "suggested_places": [
          "한강 전망 좋은 카페 - 야경 감상",
          "홍대 재즈바 - 라이브 공연",
          "24시 디저트 바 - 기념일 케이크"
        ],
        "tips": [
          "첫 장소에는 예약이 필요합니다.",
          "드레스 코드가 있는지 미리 확인하세요."
        ]
      },
      {
        "title": "감성 가득 산책",
        "description": "한적한 공간에서 대화를 나눌 수 있는 코스",
        "suggested_places": [
          "연남동 공원 산책로 - 조용한 산책",
          "북카페 - 잔잔한 음악과 독서",
          "수제 맥주 펍 - 밤의 여유를 마무리"
        ],
        "tips": [
          "산책 전 가벼운 준비 운동을 하세요.",
          "카페 좌석은 미리 체크합니다."
        ]
      }
    ]
    """

    async def fake_invoke(_template: Any, _payload: dict[str, Any]) -> str:
        return sample_response

    monkeypatch.setattr(llm, "_invoke", fake_invoke)

    result = asyncio.run(llm.generate_itinerary_suggestions(itinerary_payload))
    assert len(result) == 2
    assert all("title" in item and item["title"] for item in result)
    assert all(isinstance(item.get("suggested_places"), list) for item in result)


@pytest.mark.contract
def test_report_prompt_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_summary = "이번 달에는 방문 횟수가 늘어났고, 서로의 취향을 더 잘 이해하게 되었어요. 다음 달에는 새로운 활동에 도전해 보세요."

    async def fake_invoke(_template: Any, _payload: dict[str, Any]) -> str:
        return sample_summary

    monkeypatch.setattr(llm, "_invoke", fake_invoke)

    payload = {
        "month": "2024-05",
        "visit_count": 7,
        "top_tags": ["카페", "야경", "힐링"],
        "emotion_stats": {"설렘": 4, "안정": 3},
        "challenge_progress": 0.7,
        "notes": "챌린지 참여율이 꾸준히 상승 중",
    }

    result = asyncio.run(llm.generate_report_summary(payload))
    assert "이번 달" in result
    assert result.endswith("보세요.")
