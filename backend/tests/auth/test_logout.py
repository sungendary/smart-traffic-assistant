"""
로그아웃 테스트
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
async def test_logout():
    """로그아웃 테스트"""
    # 회원가입 및 로그인
    signup_payload = {
        "email": "logouttest@example.com",
        "password": "password123",
        "nickname": "로그아웃테스트유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "logouttest@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # 로그아웃
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await _request("POST", "/api/auth/logout", headers=headers)
    assert response.status_code == 200 or response.status_code == 204

