from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db import init  # noqa: E402
from backend.app.db.mongo import MongoConnectionManager  # noqa: E402
from backend.app.db.redis import RedisConnectionManager  # noqa: E402


class _DummyCollection:
    async def create_index(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _DummyDatabase:
    def __getitem__(self, _name: str) -> _DummyCollection:
        return _DummyCollection()


class _DummyMongoClient:
    def __init__(self) -> None:
        self._db = _DummyDatabase()

    def __getitem__(self, _name: str) -> _DummyDatabase:
        return self._db

    def close(self) -> None:
        return None


class _DummyRedisClient:
    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def stub_infrastructure(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    DB 연결을 stub으로 대체하는 fixture
    
    주의: CI 환경이나 실제 DB를 사용하는 테스트에서는 이 fixture를 비활성화해야 합니다.
    환경 변수 MONGODB_URI와 REDIS_URL이 설정되어 있으면 실제 DB를 사용합니다.
    """
    # CI 환경이나 실제 DB를 사용하는 경우 stub을 사용하지 않음
    mongodb_uri = os.getenv("MONGODB_URI", "").strip()
    redis_url = os.getenv("REDIS_URL", "").strip()
    ci_env = os.getenv("CI", "").strip().lower() in ("true", "1", "yes")
    
    # 실제 DB 연결 정보가 있거나 CI 환경이면 stub을 사용하지 않음
    if (mongodb_uri and redis_url) or ci_env:
        # CI 환경에서는 실제 DB를 사용
        print(f"[conftest] 실제 DB 사용: MONGODB_URI={mongodb_uri[:20]}..., REDIS_URL={redis_url[:20]}..., CI={ci_env}")
        return
    
    # 로컬 개발 환경에서는 stub 사용
    print("[conftest] Stub DB 사용 (로컬 개발 환경)")
    dummy_mongo_client = _DummyMongoClient()
    dummy_redis_client = _DummyRedisClient()

    async def _noop_ensure_indexes(_db: Any) -> None:
        return None

    async def _noop_close_mongo(cls: type[MongoConnectionManager]) -> None:
        return None

    async def _noop_close_redis(cls: type[RedisConnectionManager]) -> None:
        return None

    monkeypatch.setattr(
        MongoConnectionManager,
        "get_client",
        classmethod(lambda cls: dummy_mongo_client),
    )
    monkeypatch.setattr(
        RedisConnectionManager,
        "get_client",
        classmethod(lambda cls: dummy_redis_client),
    )
    monkeypatch.setattr(
        MongoConnectionManager,
        "close",
        classmethod(lambda cls: _noop_close_mongo(cls)),
    )
    monkeypatch.setattr(
        RedisConnectionManager,
        "close",
        classmethod(lambda cls: _noop_close_redis(cls)),
    )
    monkeypatch.setattr(init, "ensure_indexes", _noop_ensure_indexes)
