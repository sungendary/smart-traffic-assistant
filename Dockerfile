FROM python:3.11-slim AS base

# GitHub Packages와 저장소 연결을 위한 메타데이터 (빌드 시 --build-arg로 전달 가능)
ARG GITHUB_REPOSITORY
LABEL org.opencontainers.image.source=${GITHUB_REPOSITORY:-https://github.com/sungendary/dating-app}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

ENV PYTHONPATH=/app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
