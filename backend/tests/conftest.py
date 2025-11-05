from __future__ import annotations

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
