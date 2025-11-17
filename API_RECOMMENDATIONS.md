# 스마트 데이트 추천 API 명세

## 📍 추천 엔드포인트

### 1. 스마트 데이트 코스 추천
**POST** `/api/recommendations/recommend`

취향, 예산, 날씨를 종합적으로 고려한 개인화 데이트 코스 추천

#### Query Parameters
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `lat` | float | ✅ | 위도 | 37.5665 |
| `lon` | float | ✅ | 경도 | 126.9780 |
| `preferences` | list[str] | ❌ | 취향 태그 배열 | `["romantic", "food", "outdoor"]` |
| `budget_range` | string | ❌ | 예산 범위 | `"medium"` (기본값) |
| `emotion` | string | ❌ | 감정 상태 | `"행복한"` |
| `location_desc` | string | ❌ | 지역 설명 | `"강남역"` |

#### Budget Range Options
- `free`: 무료
- `low`: 3만원 이하
- `medium`: 3~8만원 (기본)
- `high`: 8~15만원
- `premium`: 15만원 이상

#### Preference Tags
**감정 기반:**
- `romantic`: 낭만적인
- `energetic`: 활동적인
- `relaxing`: 편안한/힐링
- `adventurous`: 모험적인
- `cultural`: 문화적인

**활동 타입:**
- `food`: 음식/맛집
- `nature`: 자연/공원
- `indoor`: 실내
- `outdoor`: 야외
- `creative`: 체험/창작

**분위기:**
- `quiet`: 조용한
- `lively`: 활기찬
- `trendy`: 트렌디한
- `classic`: 클래식/고급

#### 응답 예시
```json
{
  "weather": {
    "condition": "sunny",
    "temperature": 22.5,
    "feels_like": 21.0,
    "humidity": 55,
    "description": "맑음",
    "icon": "01d",
    "wind_speed": 2.5
  },
  "weather_suggestions": {
    "recommended_activities": [
      "야외 산책",
      "공원 피크닉",
      "한강 자전거",
      "루프탑 카페"
    ],
    "tips": [
      "자외선 차단제 필수",
      "시원한 음료 준비",
      "모자나 선글라스 착용"
    ],
    "avoid": []
  },
  "budget_info": {
    "range": "medium",
    "label": "3~8만원",
    "description": "1인 기준 3~8만원 내 장소를 추천합니다"
  },
  "recommended_places": [
    {
      "place_id": "123",
      "place_name": "한강 공원",
      "description": "야경이 아름다운 공원",
      "category_name": "공원",
      "tags": ["야외", "자연", "무료"],
      "rating": 4.6,
      "coordinates": {
        "latitude": 37.528,
        "longitude": 126.932
      },
      "recommendation_score": 0.95,
      "estimated_cost": 0
    }
  ],
  "ai_course_suggestions": [
    {
      "title": "한강 낭만 데이트 코스",
      "description": "맑은 날씨를 즐기며 한강에서 여유로운 시간을 보내세요.",
      "suggested_places": [
        "한강 공원 - 자전거 대여",
        "강변 카페 - 음료 한 잔",
        "선셋 피크닉 - 간단한 식사"
      ],
      "tips": [
        "자전거는 2시간권 추천",
        "돗자리와 간식 준비하기"
      ],
      "estimated_total_cost": 35000
    }
  ],
  "summary": {
    "total_places_found": 42,
    "after_filtering": 28,
    "top_recommendations": 10
  }
}
```

### 2. 날씨 정보 조회
**GET** `/api/recommendations/weather`

현재 위치의 날씨 정보와 데이트 활동 제안

#### Query Parameters
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `lat` | float | ✅ | 위도 |
| `lon` | float | ✅ | 경도 |

#### 응답 예시
```json
{
  "weather": {
    "condition": "rainy",
    "temperature": 15.5,
    "description": "비",
    "humidity": 85
  },
  "suggestions": {
    "recommended_activities": [
      "실내 카페",
      "영화관",
      "찜질방",
      "맛집 투어"
    ],
    "place_types": [
      "cafe_indoor",
      "movie",
      "spa",
      "restaurant"
    ],
    "tips": [
      "우산과 여벌 옷 준비",
      "따뜻한 음료 추천"
    ],
    "avoid": [
      "야외 활동",
      "산책"
    ]
  }
}
```

### 3. 예산 범위 조회
**GET** `/api/recommendations/budget-ranges`

사용 가능한 예산 범위 옵션

#### 응답 예시
```json
{
  "ranges": [
    {
      "key": "free",
      "label": "무료",
      "min": 0,
      "max": 0
    },
    {
      "key": "low",
      "label": "3만원 이하",
      "min": 0,
      "max": 30000
    },
    {
      "key": "medium",
      "label": "3~8만원",
      "min": 30000,
      "max": 80000
    }
  ]
}
```

### 4. 취향 태그 조회
**GET** `/api/recommendations/preference-tags`

사용 가능한 취향 태그 목록

#### 응답 예시
```json
{
  "categories": {
    "emotion": ["romantic", "energetic", "relaxing"],
    "activity": ["food", "nature", "indoor"],
    "mood": ["quiet", "lively", "trendy"]
  },
  "tags": {
    "romantic": {
      "keywords": ["낭만적인", "로맨틱", "감성"],
      "label": "Romantic"
    },
    "food": {
      "keywords": ["맛집", "카페", "디저트"],
      "label": "Food"
    }
  }
}
```

## 🔑 인증
모든 엔드포인트는 JWT 인증이 필요합니다.

```
Authorization: Bearer <access_token>
```

## 🌐 기본 URL
```
http://localhost:8000/api/recommendations
```

## 📝 사용 예시

### JavaScript (Fetch)
```javascript
// 스마트 추천 받기
const response = await fetch(
  'http://localhost:8000/api/recommendations/recommend?' + 
  new URLSearchParams({
    lat: 37.5665,
    lon: 126.9780,
    preferences: ['romantic', 'food'],
    budget_range: 'medium',
    emotion: '행복한',
    location_desc: '명동'
  }),
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  }
);

const data = await response.json();
console.log(data.ai_course_suggestions);
```

### Python (httpx)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        'http://localhost:8000/api/recommendations/recommend',
        params={
            'lat': 37.5665,
            'lon': 126.9780,
            'preferences': ['romantic', 'food'],
            'budget_range': 'medium',
            'emotion': '행복한'
        },
        headers={'Authorization': f'Bearer {access_token}'}
    )
    data = response.json()
```

## 🔧 필요한 환경 변수

`.env` 파일에 다음 키 추가:

```bash
# OpenWeatherMap API (무료 tier 사용 가능)
OPENWEATHER_API_KEY=your_api_key_here

# 카카오 REST API (장소 검색용, 선택)
KAKAO_REST_API_KEY=your_kakao_rest_key
```

### API 키 발급 방법

**OpenWeatherMap:**
1. https://openweathermap.org/ 회원가입
2. API Keys 메뉴에서 키 발급 (무료)
3. `.env` 파일에 추가

**카카오 REST API (선택):**
1. https://developers.kakao.com/ 로그인
2. 앱 생성 후 REST API 키 발급
3. 플랫폼 설정에서 도메인 등록
