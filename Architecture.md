# Architecture Overview

이 문서는 Smart Relationship Navigator 프로젝트의 시스템 구성을 한눈에 파악할 수 있도록 정리한 문서입니다.

## 1. 전체 아키텍처
```
┌────────────┐     ┌────────────────┐
│  Frontend  │ <-- │  FastAPI (API) │ <---> Redis (세션/캐시/레이트리밋)
│ (Native JS)│     │   + Static     │
└────────────┘     └────────────────┘
         │                    │
         ▼                    ▼
   Kakao Maps SDK       MongoDB (주 데이터 저장소)
```
- **Frontend**: 네이티브 JavaScript로 작성된 단일 페이지. FastAPI가 정적 파일(`/static`)로 제공하며, Kakao Maps SDK를 동적으로 로드합니다.
- **Backend (FastAPI)**: 인증·추천·데이터 조회 API를 제공. JWT 기반 인증과 Redis 의존 기능(레이트리밋, 토큰 블랙리스트, 외부 API 캐시)을 포함합니다.
- **MongoDB**: 사용자, 커플, 장소, 방문 기록, 배지 데이터 등 영속 데이터를 저장합니다.
- **Redis**: 로그인 시도 레이트리밋, 리프레시 토큰 관리, 외부 API 캐시, 일회성 토큰(비밀번호 재설정) 등 휘발성 데이터를 담당합니다.
- **Kakao Maps SDK**: 프론트에서 지도 렌더링과 지도 이벤트를 처리합니다.

## 2. 백엔드 구조
```
backend/
  app/
    main.py                # FastAPI 앱 초기화 및 StaticFiles 마운트
    core/
      config.py            # 환경변수 로딩(Pydantic Settings)
      security.py          # 암호화/토큰 생성 유틸리티
    api/
      routes/              # 라우터 모듈(auth, places, config, health)
      __init__.py          # APIRouter 집계
    db/
      mongo.py             # MongoDB 커넥션 관리자
      redis.py             # Redis 커넥션 관리자
    dependencies.py        # FastAPI 의존성 (DB/Redis)
    schemas/               # 요청/응답 스키마
    services/              # 비즈니스 로직 계층(users, places 등)
```
- **main.py**: lifespan 훅으로 Mongo/Redis 커넥션을 초기화하고 종료 시 정리합니다.
- **core.config**: `.env` 기반 설정 클래스. 로컬 개발에서는 `docker-compose` 기본값을 사용하고, 필요 시 `.env`에서 덮어씁니다.
- **core.security**: 비밀번호 해시(passlib), JWT 생성/검증(PyJWT), 토큰 만료 및 jti 관리 로직을 포함합니다.
- **api.routes**: 도메인별 라우터. 현재 `auth`, `places`, `config`, `health` 를 제공하며 `/api` prefix로 묶입니다.
- **services**: 사용자 생성/인증(Mongo), 장소 조회(지오쿼리 + 폴백 샘플) 등의 실제 데이터 처리를 담당합니다.

## 3. 프런트엔드 구조
```
frontend/
  index.html      # 레이아웃(좌측 로그인/설정, 중앙 지도, 우측 개인화 패널)
  styles.css      # 다크 테마 기반 스타일
  app.js          # DOM 로직, 인증 요청, Kakao 지도 초기화, 추천 호출
```
- `app.js`는 `/api/config/maps`에서 Kakao App Key를 받아 SDK를 동적으로 로드합니다.
- 로그인 성공 시 발급된 Access Token을 메모리에 저장하고, Refresh Token은 서버가 httpOnly 쿠키로 관리합니다.
- 지도 제어 버튼(현재 위치, 추천 요청), 로그인/회원가입 이벤트 핸들러를 포함합니다.

## 4. 실행 환경
### 4.1 Docker Compose (로컬 개발)
`docker-compose.yml`은 다음 서비스를 제공합니다.
- `api`: FastAPI 애플리케이션. 소스 볼륨 마운트 + `uvicorn --reload`로 자동 리로드 지원.
- `mongo`: MongoDB 6.0. 데이터 퍼시스턴스를 위해 `mongo-data` 볼륨 사용.
- `redis`: Redis 7.2. `redis-data` 볼륨 사용.

#### 사용 방법
1. `.env.example`를 참고하여 `.env` 생성 (`KAKAO_MAP_APP_KEY` 포함).
2. `docker-compose up --build` 실행.
3. 브라우저에서 `http://localhost:8000` 접속 (FastAPI가 프런트 정적 파일 제공).

### 4.2 필수 환경 변수
| 키 | 설명 |
| --- | --- |
| `MONGODB_URI` | MongoDB 접속 URI. Compose 기본값은 `mongodb://mongo:27017` |
| `MONGODB_DB` | 사용할 데이터베이스 이름 |
| `REDIS_URL` | Redis 접속 URI (`redis://redis:6379/0`) |
| `JWT_SECRET_KEY` | JWT 서명 시크릿 (프로덕션에서는 강력한 랜덤값 필요) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 만료 시간 (분) |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh Token 만료 시간 (분) |
| `KAKAO_MAP_APP_KEY` | Kakao Developers에서 발급받은 JavaScript 키 |

## 5. CI/CD 개요
### 5.1 GitHub Actions 파이프라인 예시
CI/CD에 익숙하지 않은 상황을 고려하여 최소 파이프라인 흐름을 제안합니다.
1. **Lint & Test 단계**
   - Python: `uvicorn`, `fastapi` 등 의존성 설치 → `pytest`(추후) 또는 FastAPI 앱 import 테스트.
   - ESLint 대신 기본 포맷 체크(현재는 네이티브 JS이므로 추후 확장 시 도입).
2. **Docker Build 단계**
   - `docker build -t ghcr.io/<user>/smart-love-api:<sha>`
   - 로그인 후 GHCR(또는 Docker Hub)에 푸시.
3. **(선택) Deploy 단계**
   - 개발/테스트 환경: `docker-compose pull && docker-compose up -d`를 SSH 원격 서버에서 실행.

> GitHub Actions 워크플로우 예제는 `.github/workflows/ci.yml`로 추가하는 것이 좋습니다. 현재 리포에는 없으므로, 추후 필요 시 생성해 주세요. 파이프라인에서 `.env` 대신 GitHub Secrets (`MONGODB_URI`, `REDIS_URL`, `JWT_SECRET_KEY`, `KAKAO_MAP_APP_KEY`)를 사용합니다.

## 6. Kubernetes 배포 가이드
Kubernetes 지식이 적은 상황을 가정하고, 최소 구성을 아래에 설명합니다.

1. **이미지 빌드 & 푸시**: GitHub Actions 또는 로컬에서 Docker 이미지를 레지스트리에 푸시합니다.
2. **필수 매니페스트**
   - `Deployment` (FastAPI)
   - `Service` (FastAPI를 노출, NodePort 또는 Ingress)
   - `StatefulSet` 또는 `Deployment`로 MongoDB, Redis 구성 (학습 목적이면 단일 파드도 가능)
   - `ConfigMap`/`Secret`으로 환경 변수 주입 (JWT, Kakao Key 등은 Secret)
3. **로컬 k8s 실습**
   - `kind` 또는 `k3d`로 로컬 클러스터 생성.
   - `kubectl apply -f k8s/`로 매니페스트 적용.
   - Port-forward(`kubectl port-forward svc/api 8000:8000`)를 통해 브라우저 접속.

### 6.1 제공되는 매니페스트
`k8s/` 디렉터리에 기본 리소스를 포함했습니다.

```
k8s/
  namespace.yaml            # dating-app 네임스페이스 생성
  app-configmap.yaml        # 공통 환경 변수
  app-secrets.example.yaml  # 민감 값 템플릿 (복사 후 실제 키 채워 사용)
  api-deployment.yaml       # FastAPI Deployment (health probe 포함)
  api-service.yaml          # API ClusterIP Service
  mongo-statefulset.yaml    # MongoDB StatefulSet + Headless Service + PVC
  redis-deployment.yaml     # Redis Deployment + Service
```

#### 적용 순서
1. `kubectl apply -f k8s/namespace.yaml`
2. `cp k8s/app-secrets.example.yaml k8s/app-secrets.yaml` 후 실제 `JWT_SECRET_KEY`, `KAKAO_MAP_APP_KEY` 등을 채웁니다.
3. `kubectl apply -f k8s/app-configmap.yaml`
4. `kubectl apply -f k8s/app-secrets.yaml`
5. `kubectl apply -f k8s/mongo-statefulset.yaml`
6. `kubectl apply -f k8s/redis-deployment.yaml`
7. `kubectl apply -f k8s/api-deployment.yaml`
8. `kubectl apply -f k8s/api-service.yaml`
9. 로컬 접근: `kubectl port-forward -n dating-app svc/api 8000:8000`

> `mongo-statefulset.yaml`의 `storageClassName`은 클러스터 환경에 맞게 조정하세요. kind/k3d에서는 `standard` 또는 `local-path`가 존재하는지 확인이 필요합니다. Redis는 `emptyDir`를 사용하므로, 영속 저장소가 필요하면 PVC 템플릿으로 변경하세요.


## 7. 관측성 & 운영 체크리스트
- **로그**: FastAPI 기본 로깅 + Uvicorn 로그. Docker Compose에서는 `docker-compose logs -f api`로 확인.
- **헬스체크**: `/api/health` 엔드포인트 제공. k8s `livenessProbe`/`readinessProbe`로 활용.
- **Prometheus**: 추후 `prometheus-fastapi-instrumentator` 등을 추가하여 `/metrics` 노출 가능.
- **알림**: Sentry 또는 Slack Webhook 연계를 고려.

## 8. 향후 확장 포인트
- 감정분석/추천 모델이 본격화되면, 비동기 작업 큐(RQ/Celery) + 워커 파드를 추가.
- 프런트 빌드 파이프라인을 도입(예: Vite)하여 배포 자산을 미리 번들링.
- Terraform/GitOps(ArgoCD) 등을 활용해 IaC 기반 운영으로 확장.

---
이 문서를 기반으로 프로젝트 구조를 파악하고, 로컬 개발 → Docker Compose → CI/CD → Kubernetes 순으로 작업을 확장해 나가면 됩니다. 추가적인 설정이나 스크립트가 필요하면 요청해주세요.
