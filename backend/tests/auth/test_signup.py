"""
회원가입 테스트
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
async def test_signup_success():
    """회원가입 성공 테스트"""
    payload = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "nickname": "새유저"
    }
    
    response = await _request("POST", "/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["nickname"] == "새유저"


@pytest.mark.asyncio
async def test_signup_duplicate_email():
    """중복 이메일 회원가입 실패 테스트"""
    payload = {
        "email": "duplicate@example.com",
        "password": "password123",
        "nickname": "중복유저"
    }
    
    # 첫 번째 회원가입
    response1 = await _request("POST", "/api/auth/signup", json=payload)
    assert response1.status_code == 201
    
    # 두 번째 회원가입 (중복)
    response2 = await _request("POST", "/api/auth/signup", json=payload)
    assert response2.status_code == 400 or response2.status_code == 409

