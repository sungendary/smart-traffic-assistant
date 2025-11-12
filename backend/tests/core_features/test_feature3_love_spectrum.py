"""
기능3: AI 러브 스펙트럼 (연인 관계 인사이트) 테스트
- GET /api/reports/monthly - 월간 리포트 생성
"""
import asyncio
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
async def test_monthly_report_api():
    """월간 리포트 API 테스트"""
    # 회원가입 및 로그인
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
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # 월간 리포트 조회
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await _request("GET", "/api/reports/monthly", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # 리포트 구조 확인 (데이터가 없어도 기본 구조는 반환되어야 함)
    assert isinstance(data, dict)

