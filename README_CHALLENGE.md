# 챌린지 기능 초기 설정 가이드

## 1. 초기 데이터 삽입

챌린지 기능을 사용하려면 먼저 수원특례시 내 챌린지 장소 데이터를 데이터베이스에 삽입해야 합니다.

### 방법 1: Python 스크립트 실행 (권장)

```bash
# Docker Compose 환경에서 실행
docker compose exec api python -m scripts.init_challenge_places

# 또는 로컬에서 직접 실행 (MongoDB 연결 필요)
cd backend
python scripts/init_challenge_places.py
```
## 2. 확인 방법

1. 브라우저에서 로그인 후 "챌린지" 메뉴 클릭
2. 좌측 패널에 5개의 챌린지 장소가 표시되어야 합니다
3. 각 장소에 "위치 인증" 버튼이 표시되어야 합니다

## 3. 문제 해결

### 챌린지 장소가 표시되지 않는 경우

1. **브라우저 콘솔 확인**: F12를 눌러 개발자 도구를 열고 Console 탭에서 에러 메시지 확인
2. **데이터베이스 확인**: MongoDB에 `challenge_places` 컬렉션이 생성되었는지 확인
3. **API 응답 확인**: Network 탭에서 `/api/challenges/status` 요청의 응답 확인

### 초기 데이터 삽입 스크립트 실행 오류

- MongoDB 연결 확인: `docker compose ps`로 MongoDB 컨테이너가 실행 중인지 확인
- 환경 변수 확인: `.env` 파일의 `MONGODB_URI`와 `MONGODB_DB` 값 확인

## 4. 등록되는 챌린지 장소

1. **수원 화성 성곽길** 🏛️ - 로맨틱한 산책 코스
2. **수원 남문시장** 🍜 - 전통시장 미식 투어
3. **수원시립아이파크미술관** 🎨 - 문화 예술 체험
4. **행궁동 카페거리** ☕ - 카페 데이트
5. **광교호수공원** 🌃 - 야경 감상

각 챌린지 완료 시 **500 포인트**와 **커플 배지**를 획득할 수 있습니다.





