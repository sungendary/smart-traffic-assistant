from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Coroutine

import httpx
import pytest

from backend.app.core.auth import get_current_user
from backend.app.dependencies import get_mongo_db
from backend.app.main import app
from backend.app.schemas import ChallengeProgress, Place, UserPublic
from backend.app.schemas.place import Coordinates
from backend.app.api.routes import reports as reports_route
from backend.app.services import couples, llm, map as map_service, reports, users


def configure_journey(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    sample_user = UserPublic(
        id="user-1",
        email="user@example.com",
        nickname="하루",
        email_verified=True,
        created_at=datetime.utcnow(),
        preferences=["카페", "야경"],
        couple_id="couple-1",
    )

    async def fake_db() -> Any:
        yield {"places": []}

    async def fake_list_places(
        _db: Any,
        *,
        latitude: float,
        longitude: float,
        tags: list[str] | None = None,
        limit: int = 6,
    ) -> list[Place]:
        place = Place(
            id="place-1",
            name="한강 야경 포인트",
            description="도심 야경을 즐길 수 있는 포인트",
            coordinates=Coordinates(latitude=latitude, longitude=longitude),
            tags=list(tags or ["야경"]),
            rating=4.7,
            source="stub",
        )
        return [place]

    async def fake_llm_suggestions(_payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "title": "기념일 야경 코스",
                "description": "야경과 감성 카페를 모두 즐길 수 있는 코스",
                "suggested_places": ["한강 피크닉", "감성 카페"],
                "tips": ["돗자리 준비", "카페 예약"],
            }
        ]

    async def fake_get_or_create_couple(_db: Any, user_id: str) -> dict[str, Any]:
        return {"_id": "couple-1", "members": [user_id]}

    async def fake_build_monthly_report(_db: Any, couple_id: str, month: str) -> dict[str, Any]:
        return {
            "month": month,
            "visit_count": 5,
            "top_tags": ["카페", "산책", "전시"],
            "emotion_stats": {"설렘": 3, "안정": 2},
            "challenge_progress": [
                ChallengeProgress(
                    id="challenge-1",
                    title="3주 연속 야외 데이트",
                    description="3주 동안 야외 활동을 기록하면 완료",
                    badge_icon="🌟",
                    current=2,
                    goal=3,
                    completed=False,
                    completed_at=None,
                ).model_dump()
            ],
            "summary": "이번 달에는 새로운 장소를 도전하며 좋은 추억을 쌓았습니다.",
        }

    async def fake_get_user_by_id(_db: Any, user_id: str | None) -> dict[str, Any] | None:
        if user_id != sample_user.id:
            return None
        return {
            "_id": sample_user.id,
            "email": sample_user.email,
            "nickname": sample_user.nickname,
            "email_verified": sample_user.email_verified,
            "created_at": sample_user.created_at,
            "preferences": sample_user.preferences,
            "couple_id": sample_user.couple_id,
        }

    app.dependency_overrides[get_current_user] = lambda: sample_user
    app.dependency_overrides[get_mongo_db] = fake_db
    monkeypatch.setattr(map_service, "list_places", fake_list_places)
    monkeypatch.setattr(map_service, "generate_itinerary_suggestions", fake_llm_suggestions)
    monkeypatch.setattr(llm, "generate_itinerary_suggestions", fake_llm_suggestions)
    monkeypatch.setattr(couples, "get_or_create_couple", fake_get_or_create_couple)
    monkeypatch.setattr(reports, "build_monthly_report", fake_build_monthly_report)
    monkeypatch.setattr(users, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(reports_route, "get_or_create_couple", fake_get_or_create_couple)
    monkeypatch.setattr(reports_route, "build_monthly_report", fake_build_monthly_report)

    def cleanup() -> None:
        app.dependency_overrides.clear()

    return cleanup


async def _call_app(method: str, url: str, *, json: dict[str, Any] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.request(method, url, json=json)
        await response.aread()
        return response


def run(coro: Coroutine[Any, Any, httpx.Response]) -> httpx.Response:
    return asyncio.run(coro)


@pytest.mark.journey
def test_map_suggestion_journey(monkeypatch: pytest.MonkeyPatch) -> None:
    cleanup = configure_journey(monkeypatch)
    try:
        payload = {
            "latitude": 37.55,
            "longitude": 126.92,
            "emotion": "설렘",
            "preferences": ["야경", "카페"],
            "location_text": "서울 홍대입구역",
            "additional_context": "기념일을 계획 중",
        }
        response = run(_call_app("POST", "/api/map/suggestions", json=payload))
        assert response.status_code == 200
        data = response.json()
        assert data["summary"].startswith("설렘 상태")
        assert data["llm_suggestions"][0]["title"] == "기념일 야경 코스"
    finally:
        cleanup()


@pytest.mark.journey
def test_monthly_report_journey(monkeypatch: pytest.MonkeyPatch) -> None:
    cleanup = configure_journey(monkeypatch)
    try:
        response = run(_call_app("GET", "/api/reports/monthly?month=2024-06"))
        assert response.status_code == 200
        report = response.json()
        assert report["month"] == "2024-06"
        assert report["visit_count"] == 5
        assert report["challenge_progress"][0]["title"] == "3주 연속 야외 데이트"
    finally:
        cleanup()
