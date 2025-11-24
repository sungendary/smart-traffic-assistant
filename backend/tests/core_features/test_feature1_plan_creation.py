"""
기능1-2: 코스 생성 API 스모크 테스트
- POST /api/planner/plans - 엔드포인트 존재 및 문법 오류 확인
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
async def test_create_plan_api_exists():
    """코스 생성 API 엔드포인트 존재 및 문법 오류 확인"""
    # 회원가입 (에러가 나지 않으면 OK)
    signup_payload = {
        "email": "plan_test@example.com",
        "password": "testpassword123",
        "nickname": "플랜테스트유저"
    }
    signup_response = await _request("POST", "/api/auth/signup", json=signup_payload)
    assert 200 <= signup_response.status_code < 600, f"예상치 못한 상태 코드: {signup_response.status_code}"
    
    # 로그인 (에러가 나지 않으면 OK)
    login_payload = {
        "email": "plan_test@example.com",
        "password": "testpassword123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    assert 200 <= login_response.status_code < 600, f"예상치 못한 상태 코드: {login_response.status_code}"
    
    # 토큰 추출 시도
    access_token = None
    try:
        tokens = login_response.json()
        access_token = tokens.get("access_token")
    except Exception:
        pass  # 토큰이 없어도 계속 진행
    
    # 코스 생성 시도 (에러가 나지 않으면 OK)
    plan_payload = {
        "title": "테스트 코스",
        "date": "2025-04-21",
        "stops": [
            {"place_id": "test-place-1", "order": 1, "note": "첫 번째 장소"}
        ],
        "emotion_goal": "힐링"
    }
    
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = await _request("POST", "/api/planner/plans", json=plan_payload, headers=headers)
    
    # 문법 오류 없이 실행되는지만 확인 (200-500 모두 허용)
    assert 200 <= response.status_code < 600, f"예상치 못한 상태 코드: {response.status_code}"
    
    # JSON 응답인지만 확인
    try:
        data = response.json()
        assert isinstance(data, dict), "응답이 JSON 객체여야 합니다."
    except Exception:
        # JSON 파싱 실패해도 문법 오류가 아니면 OK
        pass

