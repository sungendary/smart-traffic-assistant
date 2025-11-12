"""
Refresh Token 갱신 테스트
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
async def test_refresh_token():
    """Refresh Token으로 Access Token 갱신 테스트"""
    # 회원가입 및 로그인
    signup_payload = {
        "email": "refreshtest@example.com",
        "password": "password123",
        "nickname": "리프레시테스트유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "refreshtest@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    
    # Refresh Token 가져오기 (쿠키 또는 응답 본문에서)
    refresh_token = None
    if "refresh_token" in login_response.json():
        refresh_token = login_response.json()["refresh_token"]
    elif "refresh_token" in login_response.cookies:
        refresh_token = login_response.cookies["refresh_token"]
    
    if refresh_token:
        # Refresh Token으로 새 Access Token 발급
        response = await _request("POST", "/api/auth/refresh", cookies={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

