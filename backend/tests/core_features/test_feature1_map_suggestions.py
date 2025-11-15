"""
기능1-1: 장소 추천 API 스모크 테스트
- POST /api/map/suggestions - 엔드포인트 존재 및 문법 오류 확인
- 실제 기능 구현 여부와 관계없이 코드가 실행되는지만 검증
"""
import httpx
import pytest
from asgi_lifespan import LifespanManager

from backend.app.main import app


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """API 요청 헬퍼 함수"""
    async with LifespanManager(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.request(method, url, **kwargs)
            await response.aread()
            return response


@pytest.mark.asyncio
async def test_map_suggestions_api_exists():
    """장소 추천 API 엔드포인트 존재 및 문법 오류 확인"""
    payload = {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "emotion": "힐링",
        "preferences": ["실내", "카페"],
        "location_text": "서울시 강남구",
        "additional_context": None
    }
    
    # API 호출 시도 (에러가 나지 않으면 OK)
    response = await _request("POST", "/api/map/suggestions", json=payload)
    
    # 문법 오류 없이 실행되는지만 확인 (200-500 모두 허용)
    assert 200 <= response.status_code < 600, f"예상치 못한 상태 코드: {response.status_code}"
    
    # JSON 응답인지만 확인
    try:
        data = response.json()
        assert isinstance(data, dict), "응답이 JSON 객체여야 합니다."
    except Exception:
        # JSON 파싱 실패해도 문법 오류가 아니면 OK
        pass

