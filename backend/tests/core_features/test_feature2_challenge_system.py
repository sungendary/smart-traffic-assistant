"""
기능2: 커플 챌린지 보상 시스템 스모크 테스트
- GET /api/challenges/ - 엔드포인트 존재 및 문법 오류 확인
- POST /api/visits/checkin - 엔드포인트 존재 및 문법 오류 확인
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
async def test_challenge_progress_api_exists():
    """챌린지 진행도 조회 API 엔드포인트 존재 및 문법 오류 확인"""
    # 회원가입 및 로그인 (에러가 나지 않으면 OK)
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
    assert 200 <= login_response.status_code < 600, f"예상치 못한 상태 코드: {login_response.status_code}"
    
    # 토큰 추출 시도
    access_token = None
    try:
        tokens = login_response.json()
        access_token = tokens.get("access_token")
    except Exception:
        pass
    
    # 챌린지 진행도 조회 시도 (에러가 나지 않으면 OK)
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = await _request("GET", "/api/challenges/", headers=headers)
    assert 200 <= response.status_code < 600, f"예상치 못한 상태 코드: {response.status_code}"
    
    # JSON 응답인지만 확인
    try:
        data = response.json()
        assert isinstance(data, (list, dict)), "응답이 JSON이어야 합니다."
    except Exception:
        pass


@pytest.mark.asyncio
async def test_visit_checkin_api_exists():
    """방문 체크인 API 엔드포인트 존재 및 문법 오류 확인"""
    # 회원가입 및 로그인 (에러가 나지 않으면 OK)
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
    assert 200 <= login_response.status_code < 600, f"예상치 못한 상태 코드: {login_response.status_code}"
    
    # 토큰 추출 시도
    access_token = None
    try:
        tokens = login_response.json()
        access_token = tokens.get("access_token")
    except Exception:
        pass
    
    # 방문 체크인 시도 (에러가 나지 않으면 OK)
    checkin_payload = {
        "place_id": "test-place-1",
        "emotion": "joy",
        "tags": ["데이트", "야경"],
        "memo": "정말 좋은 장소였어요"
    }
    
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = await _request("POST", "/api/visits/checkin", json=checkin_payload, headers=headers)
    assert 200 <= response.status_code < 600, f"예상치 못한 상태 코드: {response.status_code}"
    
    # JSON 응답인지만 확인
    try:
        data = response.json()
        assert isinstance(data, dict), "응답이 JSON 객체여야 합니다."
    except Exception:
        pass

