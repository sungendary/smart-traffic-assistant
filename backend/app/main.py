from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .core.config import settings
from .db.init import ensure_indexes
from .db.mongo import MongoConnectionManager
from .db.redis import RedisConnectionManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        client = MongoConnectionManager.get_client()
        RedisConnectionManager.get_client()
        await ensure_indexes(client[settings.mongodb_db])
        logger.info("MongoDB/Redis 커넥션 초기화 및 인덱스 보장 완료")
    except Exception as exc:  # pragma: no cover
        logger.error("DB 초기화 실패: %s", exc)
    yield
    await MongoConnectionManager.close()
    await RedisConnectionManager.close()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)

app.mount("/static", StaticFiles(directory=settings.frontend_static_dir), name="static")


@app.get("/")
async def root() -> dict[str, str]:
    index_path = settings.frontend_static_dir / "index.html"
    if not index_path.exists():  # pragma: no cover
        return {"message": "Smart Relationship Navigator API"}
    return FileResponse(index_path)
