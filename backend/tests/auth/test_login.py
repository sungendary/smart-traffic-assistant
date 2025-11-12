"""
로그인 테스트
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
async def test_login_success():
    """로그인 성공 테스트"""
    # 먼저 회원가입
    signup_payload = {
        "email": "loginuser@example.com",
        "password": "loginpassword123",
        "nickname": "로그인유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    # 로그인
    login_payload = {
        "email": "loginuser@example.com",
        "password": "loginpassword123"
    }
    response = await _request("POST", "/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data or "refresh_token" in response.cookies
    assert "user" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """잘못된 자격증명으로 로그인 실패 테스트"""
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await _request("POST", "/api/auth/login", json=login_payload)
    assert response.status_code == 401 or response.status_code == 403

