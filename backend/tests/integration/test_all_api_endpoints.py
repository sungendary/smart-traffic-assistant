"""
전체 API 엔드포인트 통합 테스트
백엔드와 프론트엔드 API가 전체적으로 잘 응답하는지 검증
"""
import asyncio
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
@pytest.mark.integration
async def test_health_endpoint():
    """헬스 체크 엔드포인트 검증"""
    response = await _request("GET", "/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_config_endpoint():
    """설정 엔드포인트 검증"""
    response = await _request("GET", "/api/config/maps")
    assert response.status_code == 200
    data = response.json()
    assert "kakaoMapAppKey" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_auth_endpoints():
    """인증 관련 모든 엔드포인트 검증"""
    # 1. 회원가입
    signup_payload = {
        "email": "integration@example.com",
        "password": "integration123",
        "nickname": "통합테스트유저"
    }
    signup_response = await _request("POST", "/api/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    signup_data = signup_response.json()
    assert "user" in signup_data
    assert signup_data["user"]["email"] == "integration@example.com"
    
    # 2. 로그인
    login_payload = {
        "email": "integration@example.com",
        "password": "integration123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    access_token = login_data["access_token"]
    
    # 3. 인증된 사용자 정보 조회
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await _request("GET", "/api/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "integration@example.com"
    
    return access_token


@pytest.mark.asyncio
@pytest.mark.integration
async def test_map_endpoints():
    """장소 추천 엔드포인트 검증"""
    payload = {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "emotion": "힐링",
        "preferences": ["카페", "야경"],
        "location_text": "서울시 강남구"
    }
    response = await _request("POST", "/api/map/suggestions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "places" in data
    assert isinstance(data["places"], list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_planner_endpoints():
    """코스 관리 엔드포인트 검증"""
    # 먼저 인증 토큰 획득
    signup_payload = {
        "email": "planner_integration@example.com",
        "password": "password123",
        "nickname": "플래너테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "planner_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. 코스 목록 조회
    list_response = await _request("GET", "/api/planner/plans", headers=headers)
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)
    
    # 2. 코스 생성
    plan_payload = {
        "title": "통합 테스트 코스",
        "date": "2025-04-21",
        "stops": [
            {"place_id": "test-place-1", "order": 1, "note": "첫 번째 장소"}
        ],
        "emotion_goal": "힐링"
    }
    create_response = await _request("POST", "/api/planner/plans", json=plan_payload, headers=headers)
    assert create_response.status_code == 200
    plan_data = create_response.json()
    assert "id" in plan_data or "_id" in plan_data
    plan_id = plan_data.get("id") or plan_data.get("_id")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_challenges_endpoint():
    """챌린지 엔드포인트 검증"""
    # 인증 토큰 획득
    signup_payload = {
        "email": "challenge_integration@example.com",
        "password": "password123",
        "nickname": "챌린지테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "challenge_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 챌린지 진행도 조회
    response = await _request("GET", "/api/challenges/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_visits_endpoints():
    """방문 기록 엔드포인트 검증"""
    # 인증 토큰 획득
    signup_payload = {
        "email": "visits_integration@example.com",
        "password": "password123",
        "nickname": "방문테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "visits_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 방문 기록 목록 조회
    list_response = await _request("GET", "/api/visits/", headers=headers)
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_reports_endpoint():
    """리포트 엔드포인트 검증"""
    # 인증 토큰 획득
    signup_payload = {
        "email": "reports_integration@example.com",
        "password": "password123",
        "nickname": "리포트테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "reports_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 월간 리포트 조회
    response = await _request("GET", "/api/reports/monthly", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "month" in data or "visit_count" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bookmarks_endpoints():
    """북마크 엔드포인트 검증"""
    # 인증 토큰 획득
    signup_payload = {
        "email": "bookmarks_integration@example.com",
        "password": "password123",
        "nickname": "북마크테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "bookmarks_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 북마크 목록 조회
    list_response = await _request("GET", "/api/bookmarks/", headers=headers)
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_couples_endpoint():
    """커플 정보 엔드포인트 검증"""
    # 인증 토큰 획득
    signup_payload = {
        "email": "couples_integration@example.com",
        "password": "password123",
        "nickname": "커플테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_payload = {
        "email": "couples_integration@example.com",
        "password": "password123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 커플 정보 조회
    response = await _request("GET", "/api/couples/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data or "_id" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_api_flow():
    """전체 API 플로우 통합 테스트"""
    # 1. 헬스 체크
    health_response = await _request("GET", "/api/health")
    assert health_response.status_code == 200
    
    # 2. 회원가입 및 로그인
    signup_payload = {
        "email": "complete_flow@example.com",
        "password": "password123",
        "nickname": "전체플로우테스트"
    }
    await _request("POST", "/api/auth/signup", json=signup_payload)
    
    login_response = await _request("POST", "/api/auth/login", json={
        "email": "complete_flow@example.com",
        "password": "password123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 3. 주요 API 엔드포인트 호출
    endpoints_to_test = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/planner/plans"),
        ("GET", "/api/challenges/"),
        ("GET", "/api/visits/"),
        ("GET", "/api/bookmarks/"),
        ("GET", "/api/couples/me"),
        ("GET", "/api/reports/monthly"),
    ]
    
    for method, endpoint in endpoints_to_test:
        response = await _request(method, endpoint, headers=headers)
        assert response.status_code in [200, 201, 204], f"{method} {endpoint} failed with {response.status_code}"
    
    # 4. 장소 추천 API
    map_response = await _request("POST", "/api/map/suggestions", json={
        "latitude": 37.5665,
        "longitude": 126.9780,
        "emotion": "힐링",
        "preferences": ["카페"],
        "location_text": "서울"
    })
    assert map_response.status_code == 200
    
    print("✅ 모든 API 엔드포인트가 정상적으로 응답합니다!")

