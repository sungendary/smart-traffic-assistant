from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from .api import api_router
from .core.config import settings
from .db.mongo import MongoConnectionManager
from .db.redis import RedisConnectionManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 커넥션 미리 생성
    try:
        MongoConnectionManager.get_client()
        RedisConnectionManager.get_client()
        logger.info("데이터베이스/Redis 커넥션 초기화 완료")
    except Exception as exc:  # pragma: no cover - 초기 연결 실패 로깅
        logger.warning("초기 커넥션 생성 중 오류 발생: %s", exc)
    yield
    # 종료 시 커넥션 정리
    await RedisConnectionManager.close()
    await MongoConnectionManager.close()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)

frontend_dir = settings.frontend_static_dir
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend_index() -> FileResponse:
    index_path = Path(frontend_dir, "index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html 파일을 찾을 수 없습니다.")
    return FileResponse(index_path)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    icon_path = Path(frontend_dir, "favicon.ico")
    if icon_path.exists():
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="favicon을 찾을 수 없습니다.")
