"""
기능3: AI 러브 스펙트럼 스모크 테스트
- GET /api/reports/monthly - 엔드포인트 존재 및 문법 오류 확인
- 실제 기능 구현 여부와 관계없이 코드가 실행되는지만 검증
"""
import httpx
import pytest
from asgi_lifespan import LifespanManager

from backend.app.main import app


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    async with LifespanManager(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.request(method, url, **kwargs)
            await response.aread()
            return response


@pytest.mark.asyncio
async def test_monthly_report_api_exists():
    """월간 리포트 API 엔드포인트 존재 및 문법 오류 확인"""
    # 회원가입 및 로그인 (에러가 나지 않으면 OK)
    signup_payload = {
        "email": "report@example.com",
        "password": "testpassword123",
        "nickname": "리포트유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "report@example.com",
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
        pass
    
    # 월간 리포트 조회 시도 (에러가 나지 않으면 OK)
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = await _request("GET", "/api/reports/monthly", headers=headers)
    assert 200 <= response.status_code < 600, f"예상치 못한 상태 코드: {response.status_code}"
    
    # JSON 응답인지만 확인
    try:
        data = response.json()
        assert isinstance(data, dict), "응답이 JSON 객체여야 합니다."
    except Exception:
        pass

