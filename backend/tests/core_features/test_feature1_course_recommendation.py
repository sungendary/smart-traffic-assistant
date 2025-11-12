"""
기능1: 취향 기반 데이트 코스 추천 테스트
- POST /api/map/suggestions - 장소 추천 API
- POST /api/planner/plans - 코스 생성 API
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
async def test_map_suggestions_api():
    """장소 추천 API 테스트 - 실제 코드 검증"""
    # 실제 API 스펙에 맞는 요청
    payload = {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "emotion": "힐링",
        "preferences": ["실내", "카페"],  # 실제 스키마에 맞게 수정
        "location_text": "서울시 강남구",
        "additional_context": None
    }
    
    # 실제 FastAPI 앱의 /api/map/suggestions 엔드포인트 호출
    # -> backend/app/api/routes/map.py의 suggest_places 함수 실행
    # -> backend/app/services/map.py의 get_map_suggestions 함수 실행
    response = await _request("POST", "/api/map/suggestions", json=payload)
    
    # 실제 코드가 제대로 작동하는지 검증
    assert response.status_code == 200, f"API 호출 실패: {response.status_code} - {response.text}"
    data = response.json()
    
    # 실제 서비스 함수가 반환하는 구조 검증
    # backend/app/services/map.py의 get_map_suggestions가 반환하는 구조 확인
    assert "places" in data, "응답에 'places' 필드가 없습니다. 실제 코드가 변경되었을 수 있습니다."
    assert "summary" in data or "llm_suggestions" in data, "응답 구조가 예상과 다릅니다."
    assert isinstance(data["places"], list), "'places'는 리스트여야 합니다."
    
    # 실제 데이터가 반환되었는지 확인
    if len(data["places"]) > 0:
        place = data["places"][0]
        assert "id" in place or "place_id" in place or "_id" in place, "장소 데이터 구조가 올바르지 않습니다."


@pytest.mark.asyncio
async def test_create_plan_api():
    """코스 생성 API 테스트 - 실제 코드 검증"""
    # 실제 인증 플로우 테스트 (backend/app/api/routes/auth.py 실행)
    signup_payload = {
        "email": "plan_test@example.com",
        "password": "testpassword123",
        "nickname": "플랜테스트유저"
    }
    signup_response = await _request("POST", "/api/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201, "회원가입 실패 - 실제 코드 문제 가능"
    signup_data = signup_response.json()
    assert "user" in signup_data, "회원가입 응답 구조가 변경되었습니다."
    
    login_payload = {
        "email": "plan_test@example.com",
        "password": "testpassword123"
    }
    login_response = await _request("POST", "/api/auth/login", json=login_payload)
    assert login_response.status_code == 200, "로그인 실패 - 실제 코드 문제 가능"
    tokens = login_response.json()
    assert "access_token" in tokens, "토큰 발급 실패 - 실제 인증 코드 문제 가능"
    access_token = tokens["access_token"]
    
    # 실제 코스 생성 API 테스트
    # -> backend/app/api/routes/planner.py의 create_new_plan 함수 실행
    # -> backend/app/services/planner.py의 create_plan 함수 실행
    plan_payload = {
        "title": "테스트 코스",
        "date": "2025-04-21",
        "stops": [
            {"place_id": "test-place-1", "order": 1, "note": "첫 번째 장소"}
        ],
        "emotion_goal": "힐링"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await _request("POST", "/api/planner/plans", json=plan_payload, headers=headers)
    
    # 실제 코드가 제대로 작동하는지 엄격하게 검증
    assert response.status_code == 200, f"코스 생성 실패: {response.status_code} - {response.text}"
    data = response.json()
    
    # 실제 서비스 함수가 반환하는 구조 검증
    # backend/app/services/planner.py의 create_plan이 반환하는 구조 확인
    assert "id" in data or "_id" in data, "생성된 코스에 ID가 없습니다. 실제 코드가 변경되었을 수 있습니다."
    assert data["title"] == "테스트 코스", "코스 제목이 저장되지 않았습니다."
    assert "couple_id" in data or "coupleId" in data, "커플 ID가 없습니다. 실제 로직 문제 가능."
    assert "stops" in data, "코스의 stops 정보가 없습니다."
    assert len(data["stops"]) == 1, "stops 개수가 맞지 않습니다."

