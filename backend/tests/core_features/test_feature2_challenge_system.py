"""
기능2: 커플 챌린지 보상 시스템 테스트
- GET /api/challenges/ - 챌린지 진행도 조회
- POST /api/visits/checkin - 방문 체크인
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
async def test_challenge_progress_api():
    """챌린지 진행도 조회 API 테스트"""
    # 회원가입 및 로그인
    signup_payload = {
        "email": "challenge@example.com",
        "password": "testpassword123",
        "nickname": "챌린지유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "challenge@example.com",
        "password": "testpassword123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # 챌린지 진행도 조회
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await _request("GET", "/api/challenges/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)  # 챌린지 목록 반환


@pytest.mark.asyncio
async def test_visit_checkin_api():
    """방문 체크인 API 테스트"""
    # 회원가입 및 로그인
    signup_payload = {
        "email": "visit@example.com",
        "password": "testpassword123",
        "nickname": "방문유저"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "visit@example.com",
        "password": "testpassword123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # 방문 체크인
    checkin_payload = {
        "place_id": "test-place-1",
        "emotion": "joy",
        "tags": ["데이트", "야경"],
        "memo": "정말 좋은 장소였어요"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await _request("POST", "/api/visits/checkin", json=checkin_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data or "_id" in data

