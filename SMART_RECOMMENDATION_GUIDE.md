# 🌟 스마트 데이트 추천 기능 사용 가이드

## 📖 개요

이 기능은 **취향, 예산, 날씨**를 종합적으로 고려하여 커플에게 최적의 데이트 코스를 추천합니다.

## 🎯 주요 특징

### 1. 실시간 날씨 기반 추천
- OpenWeatherMap API를 통해 현재 위치의 날씨를 실시간으로 확인
- 날씨 상태에 따른 활동 제안
  - ☀️ **맑음**: 야외 산책, 한강 자전거, 루프탑 카페
  - 🌧️ **비**: 실내 카페, 영화관, 찜질방, 맛집 투어
  - ❄️ **눈**: 눈 구경 산책, 따뜻한 카페, 온천
  - ⛈️ **폭풍**: 안전한 실내 활동 추천

### 2. 예산 범위 필터링
5가지 예산 범위 제공:
- 💚 **무료**: 공원, 한강, 무료 전시
- 💛 **3만원 이하**: 카페, 박물관, 간단한 식사
- 💙 **3~8만원**: 레스토랑, 액티비티, 쇼핑
- 💜 **8~15만원**: 고급 레스토랑, 공연, 체험
- 🖤 **15만원 이상**: 프리미엄 코스, 특별한 경험

### 3. 취향 기반 개인화
다양한 취향 태그 지원:

**감정 기반**
- 🌹 romantic: 낭만적인 분위기
- ⚡ energetic: 활동적인 액티비티
- 🌿 relaxing: 편안한 힐링
- 🎯 adventurous: 모험적인 경험
- 🎨 cultural: 문화/예술 체험

**활동 타입**
- 🍽️ food: 맛집/카페/디저트
- 🌳 nature: 자연/공원/산/바다
- 🏠 indoor: 실내 활동
- 🚶 outdoor: 야외 활동
- ✨ creative: 체험/공방/창작

**분위기**
- 🤫 quiet: 조용하고 한적한
- 🎉 lively: 활기차고 북적이는
- 📸 trendy: 트렌디하고 핫한
- 👔 classic: 클래식하고 고급스러운

### 4. AI 코스 생성
LangChain + Ollama를 활용하여:
- 날씨와 예산을 고려한 3가지 데이트 코스 제안
- 각 코스별 추천 장소와 이동 동선
- 실용적인 팁 제공

## 🚀 사용 방법

### 1. 프론트엔드에서 사용

1. **로그인** 후 지도 화면으로 이동
2. 좌측 사이드바에서 **예산 범위** 선택
3. 원하는 **취향 태그** 클릭 (여러 개 선택 가능)
4. **감정 상태**와 **지역** 입력 (선택)
5. **💡 스마트 추천 받기** 버튼 클릭

### 2. API로 직접 호출

```bash
curl -X POST "http://localhost:8000/api/recommendations/recommend?lat=37.5665&lon=126.9780&preferences=romantic&preferences=food&budget_range=medium&emotion=행복한&location_desc=강남역" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Python 코드 예시

```python
import httpx

async def get_smart_recommendations():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8000/api/recommendations/recommend',
            params={
                'lat': 37.5665,
                'lon': 126.9780,
                'preferences': ['romantic', 'food'],
                'budget_range': 'medium',
                'emotion': '행복한',
                'location_desc': '강남역'
            },
            headers={'Authorization': f'Bearer {access_token}'}
        )
        return response.json()
```

## 📊 응답 데이터 구조

```json
{
  "weather": {
    "condition": "sunny",
    "temperature": 22.5,
    "description": "맑음",
    "humidity": 55
  },
  "weather_suggestions": {
    "recommended_activities": ["야외 산책", "공원 피크닉"],
    "tips": ["자외선 차단제 필수", "시원한 음료 준비"]
  },
  "budget_info": {
    "range": "medium",
    "label": "3~8만원"
  },
  "recommended_places": [
    {
      "place_name": "한강 공원",
      "recommendation_score": 0.95,
      "estimated_cost": 0,
      "rating": 4.6
    }
  ],
  "ai_course_suggestions": [
    {
      "title": "한강 낭만 데이트 코스",
      "suggested_places": ["한강 공원", "강변 카페"],
      "tips": ["자전거 2시간권 추천"],
      "estimated_total_cost": 35000
    }
  ]
}
```

## 🔧 추천 알고리즘

장소 점수는 다음 3가지 요소로 계산됩니다:

1. **선호도 점수 (40%)**: 선택한 취향 태그와 장소의 매칭도
2. **날씨 적합도 (35%)**: 현재 날씨에 적합한 활동인지
3. **예산 적합도 (25%)**: 선택한 예산 범위에 맞는지

최종 점수가 높은 순으로 정렬되어 반환됩니다.

## 🌐 필요한 API 키

### OpenWeatherMap (필수)
1. https://openweathermap.org/ 회원가입
2. API Keys 메뉴에서 무료 키 발급
3. `.env` 파일에 추가:
   ```bash
   OPENWEATHER_API_KEY=your_api_key_here
   ```

### Kakao REST API (선택)
장소 검색 기능을 사용하려면:
1. https://developers.kakao.com/ 로그인
2. 앱 생성 후 REST API 키 발급
3. `.env` 파일에 추가:
   ```bash
   KAKAO_REST_API_KEY=your_kakao_key_here
   ```

## 💡 활용 팁

### 날씨별 추천 예시

**맑은 날 (sunny)**
- 예산: low
- 취향: nature, outdoor
- 결과: 한강 공원, 남산 둘레길, 무료 야외 콘서트

**비 오는 날 (rainy)**
- 예산: medium
- 취향: indoor, romantic
- 결과: 감성 카페, 실내 전시, 아늑한 레스토랑

**추운 겨울 (snowy)**
- 예산: high
- 취향: relaxing, food
- 결과: 찜질방, 온천, 따뜻한 국물 맛집

### 상황별 추천 설정

**첫 데이트**
- 예산: medium
- 취향: quiet, romantic, food
- 감정: 설레는

**기념일**
- 예산: high
- 취향: romantic, trendy
- 감정: 행복한

**힐링 데이트**
- 예산: low
- 취향: relaxing, nature, quiet
- 감정: 힐링

**액티브 데이트**
- 예산: medium
- 취향: energetic, outdoor
- 감정: 즐거움

## 🐛 트러블슈팅

### 날씨 정보가 안 나와요
- OpenWeatherMap API 키가 올바르게 설정되었는지 확인
- API 키의 사용량 제한을 초과하지 않았는지 확인
- 백엔드 로그에서 에러 메시지 확인

### 추천 장소가 적어요
- MongoDB에 장소 데이터가 충분히 있는지 확인
- 예산 범위를 넓혀보세요 (medium → high)
- 취향 태그를 줄여보세요 (너무 많으면 매칭이 어려울 수 있음)

### AI 코스가 생성 안 돼요
- Ollama 서비스가 실행 중인지 확인
- LLM 모델이 다운로드되어 있는지 확인
- 네트워크 연결 상태 확인

## 📈 향후 개선 계획

- [ ] 과거 방문 기록 기반 추천
- [ ] 커플 취향 학습 및 자동 프로필 생성
- [ ] 실시간 혼잡도 정보 반영
- [ ] 대중교통 소요 시간 계산
- [ ] 코스 북마크 및 공유 기능
- [ ] 날씨 예보 기반 미래 데이트 추천

## 📞 문의

기능 관련 문의나 버그 리포트는 GitHub Issues로 남겨주세요!
