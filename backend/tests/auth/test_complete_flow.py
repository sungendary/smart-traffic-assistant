"""
전체 인증 플로우 통합 테스트
회원가입 → 로그인 → 토큰 사용 → 로그아웃
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
async def test_complete_auth_flow():
    """전체 인증 플로우 테스트"""
    email = "flowtest@example.com"
    password = "flowpassword123"
    nickname = "플로우테스트유저"
    
    # 1. 회원가입
    signup_payload = {
        "email": email,
        "password": password,
        "nickname": nickname
    }
    signup_response = await _request("POST", "/api/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    
    # 2. 로그인
    login_payload = {
        "email": email,
        "password": password
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # 3. 인증된 사용자 정보 조회
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await _request("GET", "/api/auth/me", headers=headers)
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == email
    assert user_data["nickname"] == nickname
    
    # 4. 로그아웃
    logout_response = await _request("POST", "/api/auth/logout", headers=headers)
    assert logout_response.status_code == 200 or logout_response.status_code == 204

