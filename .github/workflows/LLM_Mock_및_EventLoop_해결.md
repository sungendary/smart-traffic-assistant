# LLM Mock 및 Event Loop 문제 해결

## 발견된 문제들

### 1. ❌ LLM 서비스 연결 실패

**문제:**
- `Cannot connect to host llm:11434` 에러 발생
- `get_llm()` 함수가 `@lru_cache`로 데코레이트되어 있어서 실제 연결을 시도
- Mock이 설정되기 전에 `ChatOllama` 인스턴스가 생성됨

**원인:**
- `get_llm()` 함수가 `@lru_cache`로 캐시되어 있어서, mock을 설정하기 전에 호출되면 실제 `ChatOllama` 인스턴스를 생성하려고 시도
- `ChatOllama` 클래스가 실제로 `llm:11434`에 연결을 시도

**해결:**
- `get_llm()` 함수 자체를 mock으로 대체
- `ChatOllama` 클래스 자체를 mock으로 대체 (이중 보호)
- `generate_itinerary_suggestions`와 `generate_report_summary` 함수도 mock으로 대체 (이중 보호)

### 2. ❌ Event Loop 문제

**문제:**
- `RuntimeError: Event loop is closed` 에러 발생
- `LifespanManager`가 이벤트 루프를 닫는 것 같음
- 여러 번 `_request`를 호출할 때 문제 발생

**원인:**
- `pytest.ini`에 asyncio 설정이 없어서 이벤트 루프 관리가 제대로 되지 않음
- `LifespanManager`가 이벤트 루프를 닫는 것 같음

**해결:**
- `pytest.ini`에 asyncio 모드 설정 추가:
  ```ini
  asyncio_mode = auto
  asyncio_default_fixture_loop_scope = function
  ```

## 수정된 내용

### backend/tests/conftest.py

1. **LLM mock fixture 개선:**
   ```python
   @pytest.fixture(autouse=True)
   def mock_llm_service(monkeypatch: pytest.MonkeyPatch) -> None:
       # get_llm() 함수의 캐시 클리어
       llm_service.get_llm.cache_clear()
       
       # Mock ChatOllama 클래스 생성
       class MockChatOllama:
           async def ainvoke(self, *args, **kwargs):
               return MockResponse()
       
       # get_llm() 함수를 mock으로 대체
       monkeypatch.setattr(llm_service, "get_llm", mock_get_llm)
       
       # ChatOllama 클래스 자체를 mock으로 대체 (이중 보호)
       monkeypatch.setattr(chat_models, "ChatOllama", MockChatOllama)
       
       # generate 함수들도 mock으로 대체 (이중 보호)
       monkeypatch.setattr(llm_service, "generate_itinerary_suggestions", ...)
       monkeypatch.setattr(llm_service, "generate_report_summary", ...)
   ```

### pytest.ini

1. **Asyncio 설정 추가:**
   ```ini
   asyncio_mode = auto
   asyncio_default_fixture_loop_scope = function
   ```

## 예상 결과

이제 다음이 해결됩니다:

1. ✅ **LLM 연결 실패**: `get_llm()` 함수와 `ChatOllama` 클래스가 mock으로 대체되어 실제 연결 시도 없음
2. ✅ **Event Loop 문제**: `pytest.ini`에 asyncio 설정 추가로 이벤트 루프 관리 개선

## 추가 확인 사항

만약 여전히 문제가 발생한다면:

1. **LLM mock이 작동하지 않는 경우:**
   - `get_llm()` 함수의 캐시가 제대로 클리어되었는지 확인
   - `ChatOllama` 클래스 mock이 제대로 설정되었는지 확인

2. **Event loop 문제가 계속되는 경우:**
   - `LifespanManager` 사용 방식을 변경 (fixture로 만들어서 재사용)
   - 각 테스트마다 새로운 이벤트 루프를 생성하도록 설정

## 다음 단계

1. CI를 다시 실행하여 문제가 해결되었는지 확인
2. 실패 로그를 확인하여 추가 문제가 있는지 확인
3. 필요시 추가 수정

