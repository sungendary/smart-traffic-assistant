# Smart Relationship Navigator

지도 기반 커플 데이트 추천 플랫폼입니다. FastAPI 백엔드와 네이티브 JavaScript 프런트엔드를 사용하며, Docker 및 Kubernetes 환경에서 실행할 수 있도록 구성되어 있습니다.

## 주요 기능
- 자체 회원가입/로그인 + JWT 무상태 인증 (Refresh 토큰은 Redis에 보관)
- Kakao Maps 기반 지도 렌더링 및 주변 장소 추천
- MongoDB 지오스패셜 쿼리를 활용한 위치 기반 장소 조회 (데이터 없을 시 샘플 응답)
- Redis를 이용한 레이트리밋/토큰 블랙리스트/캐싱 준비
- LangChain + 로컬 Ollama LLM(Qwen 0.5B 경량 모델) 기반 데이트 코스 추천 API 제공
- Docker Compose / Kubernetes 배포 템플릿 및 GitHub Actions CI 파이프라인 제공

## 기술 스택
- Backend: FastAPI, Motor(MongoDB), Redis-py, LangChain
- Frontend: Native JavaScript, Kakao Maps SDK
- Database: MongoDB (주 저장소), Redis (필수 인프라)
- Auth: JWT(access/refresh), Argon2/Bcrypt 해시
- DevOps: Docker, Docker Compose, Kubernetes(k3d/kind), GitHub Actions, GHCR, Ollama

## 환경 변수
`.env.example`를 복사해 `.env`를 생성하고 값을 채워주세요. 주요 키는 다음과 같습니다.

| 키 | 설명 |
| --- | --- |
| `MONGODB_URI` | MongoDB 접속 URI (`mongodb://mongo:27017`) |
| `MONGODB_DB` | 데이터베이스 이름 (`datingapp`) |
| `REDIS_URL` | Redis 접속 URI (`redis://redis:6379/0`) |
| `JWT_SECRET_KEY` | 32자 이상의 랜덤 시크릿. 예) `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `KAKAO_MAP_APP_KEY` | Kakao Developers JavaScript 키 |
| `LLM_BASE_URL` | LangChain이 접근할 LLM 엔드포인트 (`http://llm:11434`) |
| `LLM_MODEL` | Ollama 모델 이름 (예: `qwen2.5:0.5b`, `llama3:instruct`) |
| `LLM_TEMPERATURE` | LangChain temperature 값 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access 토큰 만료(분) |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh 토큰 만료(분) |
| `PASSWORD_HASH_SCHEME` | `argon2` 또는 `bcrypt` |
| `CORS_ORIGINS` | 허용할 Origin 목록 (쉼표 구분) |

> Kubernetes 배포 시 `k8s/app-secrets.example.yaml`를 복사(예: `app-secrets.yaml`)하여 동일한 값을 넣어야 합니다.

## 로컬 개발 (Docker Compose)
1. `.env` 파일을 준비합니다.
2. Docker Desktop 또는 호환 런타임을 실행합니다.
3. Docker Compose 명령 사용법
   - 첫 빌드 및 기동:  
     ```bash
     docker compose up --build
     ```
   - 백그라운드(데몬) 실행:  
     ```bash
     docker compose up -d
     ```
   - 로그 확인:  
     ```bash
     docker compose logs -f api
     ```
   - 서비스 재시작/정지/삭제:  
     ```bash
     docker compose restart api      # FastAPI만 재시작
     docker compose stop             # 모든 컨테이너 정지
     docker compose down             # 정지 + 네트워크 정리
     docker compose down -v          # 정지 + 볼륨 삭제(데이터 초기화)
     ```
4. 브라우저에서 `http://localhost:8000` 접속 → 회원가입 후 로그인 → “주변 추천받기” 버튼으로 지도/추천 검증
5. (선택) MongoDB 지오 인덱스 생성:  
   ```bash
   docker compose exec mongo mongosh --quiet --eval 'db=getSiblingDB("datingapp");db.places.createIndex({location:"2dsphere"})'
   ```
6. LangChain용 경량 LLM 모델 다운로드(최초 1회):
   ```bash
   docker compose exec llm ollama pull qwen2.5:0.5b
   ```
   `.env`에서 `LLM_MODEL` 값을 변경했다면 동일한 명령으로 원하는 모델을 추가로 받아야 합니다.
   
   > `llm` 서비스가 없어서 `service "llm" is not running` 오류가 나면 `docker-compose.yml`에 아래 블록이 포함되어 있는지 확인한 뒤 `docker compose up -d llm`으로 컨테이너를 기동하세요.
   > ```yaml
   >   llm:
   >     image: ollama/ollama:latest
   >     container_name: dating-app-llm
   >     restart: unless-stopped
   >     ports:
   >       - "11434:11434"
   >     volumes:
   >       - llm-models:/root/.ollama
   >     environment:
   >       - OLLAMA_NUM_PARALLEL=1
   >       - OLLAMA_MAX_LOADED_MODELS=1
   > ```
   
   > `docker-compose.yml`에는 `cpus`/`mem_limit`를 낮게 설정해 두었습니다(맥북 기본 모델 기준). 필요 시 값을 조정하세요.

## 쿠버네티스 배포
처음 Kubernetes를 쓰는 팀원이 헷갈리지 않도록, 로컬 테스트 환경(minikube) 기준으로 단계별 설명을 제공합니다. 다른 클러스터(EKS/GKE 등)를 사용할 때도 “이미지 준비 → 매니페스트 적용” 순서는 동일합니다.

### 0. 사전 준비
- `.env`에 입력한 값과 동일하게 `k8s/app-secrets.yaml`을 준비합니다.
  # 편집해서 JWT_SECRET_KEY, KAKAO_MAP_APP_KEY 등 실제 값 입력
- `kubectl version --client`로 kubectl이 설치되어 있는지 확인합니다.

### 1. 로컬 클러스터 생성 (minikube 예시)
1. minikube 설치 (macOS: `brew install minikube`, Windows: 공식 설치 프로그램).
2. 리소스를 넉넉히 잡아 클러스터를 시작합니다.
   ```bash
   minikube start --profile dating-app --cpus 4 --memory 4096
   ```
   > kind/k3d를 사용한다면 해당 도구의 클러스터 생성 명령을 사용합니다.

### 2. 애플리케이션 이미지 준비
쿠버네티스 파드는 레지스트리에서 이미지를 가져옵니다. 아래 두 가지 방법 중 하나를 선택하세요.

**옵션 A — 레지스트리에 푸시 (권장)**
1. GHCR 기준 수동 푸시 예시는 다음과 같습니다.
   ```bash
   docker build -t ghcr.io/<your-id>/dating-app-api:latest .
   docker push ghcr.io/<your-id>/dating-app-api:latest
   ```
2. `k8s/api-deployment.yaml`의 `image` 필드를 위 경로로 수정합니다.
3. 사설 레지스트리를 쓸 경우 `imagePullSecrets`를 Deployment에 추가해야 합니다.

**옵션 B — minikube Docker 데몬에 직접 빌드**
1. minikube의 Docker 환경으로 전환합니다.
   ```bash
   eval "$(minikube -p dating-app docker-env)"
   ```
2. 이미지 빌드:
   ```bash
   docker build -t dating-app-api:latest .
   ```
3. 원래 환경으로 복구:
   ```bash
   eval "$(minikube docker-env -u)"
   ```
4. `k8s/api-deployment.yaml`에서 `image: dating-app-api:latest`인지 확인합니다. 레지스트리에 올리지 않아도 minikube 내부에서 이미지를 사용할 수 있습니다.

### 3. 매니페스트 적용
`k8s/` 디렉터리에는 네임스페이스, ConfigMap/Secret, MongoDB/Redis, API 배포가 모두 준비되어 있습니다. 아래 순서를 그대로 실행하면 됩니다.
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/app-configmap.yaml
kubectl apply -f k8s/app-secrets.yaml
kubectl apply -f k8s/mongo-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
kubectl apply -f k8s/llm-deployment.yaml
```
배포 상태 확인:
```bash
kubectl get pods -n dating-app
kubectl logs -n dating-app deployment/dating-app-api
```

### 4. 서비스 접속 및 검증
- 포트포워딩 방식으로 빠르게 접속할 수 있습니다.
  ```bash
  kubectl port-forward -n dating-app svc/api 8000:8000
  ```
  접속 후 `http://localhost:8000`에서 회원가입/로그인, “주변 추천받기” 버튼을 확인하세요.
- minikube 사용 시 NodePort/LoadBalancer가 필요하면 `minikube service -n dating-app api --url`을 사용할 수 있습니다.

### 5. 정리 및 추가 설정
- 실습을 종료하려면:
  ```bash
  kubectl delete namespace dating-app
  minikube delete --profile dating-app
  ```
- `mongo-statefulset.yaml`의 `storageClassName`은 클러스터 환경(예: minikube=standard, kind/k3d=local-path 등)에 맞게 조정하세요.
- Redis는 `emptyDir`를 사용하므로 영속 데이터가 필요하면 PVC를 추가하십시오.
- LLM을 사용하는 경우 `kubectl exec -it deploy/llm -n dating-app -- ollama pull qwen2.5:0.5b` 명령으로 원하는 모델을 로드한 뒤 `/api/ai/suggest-itinerary` 기능을 호출할 수 있습니다. (모델명은 `.env`의 `LLM_MODEL`과 동일해야 합니다.)

이 과정을 따르면 협업 중 처음 쿠버네티스를 접하는 사람도 “클러스터 생성 → 이미지 준비 → 매니페스트 적용 → 접속 확인” 흐름을 문제없이 수행할 수 있습니다.

## GitHub Actions CI/CD
`.github/workflows/ci.yml` 파이프라인이 포함되어 있습니다.

- `lint-and-compile` 작업: Python 의존성 설치 후 `python -m compileall backend/app`
- `docker-build-push` 작업 (main 브랜치 push 시): GHCR 로그인 → Docker 이미지 빌드/푸시 → k8s 매니페스트와 Docker Compose 파일을 아티팩트로 업로드

### 필수 GitHub Secrets
| Secret | 설명 |
| --- | --- |
| `GITHUB_TOKEN` | 기본 제공. GHCR 푸시에 사용 (추가 설정 불필요) |
| `KAKAO_MAP_APP_KEY` 등 | 애플리케이션 실행에 필요한 값은 필요 시 Workflow `env`로 주입할 수 있습니다. |

> 레지스트리 네임스페이스를 바꾸려면 `IMAGE_NAME` 환경 변수를 수정하세요.

## 프로젝트 구조
```
backend/
  app/
    api/routes/...       # FastAPI 라우트(인증, 장소, 설정, 헬스)
    core/                # 설정/보안 유틸
    db/                  # MongoDB/Redis 커넥션
    services/            # 도메인 로직
    schemas/             # Pydantic 모델
frontend/
  index.html             # 레이아웃 (좌/중/우 패널)
  app.js                 # Kakao 지도 + 인증/추천 로직
  styles.css             # 다크 테마 스타일
k8s/
  *.yaml                 # Namespace, ConfigMap, Secret 템플릿, Deployments
.github/workflows/
  ci.yml                 # GitHub Actions 파이프라인
Dockerfile
docker-compose.yml
Architecture.md          # 아키텍처 상세 문서
Document/개발문서.md     # 한글 요구사항 및 설계
```

## 다음 단계
- MongoDB 지오 인덱스 및 샘플 데이터 적재 자동화 (Startup 스크립트 또는 Seed 작업)
- Redis 기반 레이트리밋/토큰 블랙리스트 로직 구현
- 추천/감정분석 모델 파이프라인 확장 (TensorFlow 등)
- 프런트엔드 상태 관리/빌드 파이프라인(예: Vite) 도입 검토

궁금한 점이나 추가 자동화(예: Helm Chart, Terraform, 배포 스크립트)가 필요하면 이슈나 Pull Request로 요청해 주세요.