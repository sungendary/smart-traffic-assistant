from __future__ import annotations

import asyncio

import httpx
from asgi_lifespan import LifespanManager
import pytest

from backend.app.main import app


async def _request(method: str, url: str) -> httpx.Response:
    async with LifespanManager(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.request(method, url)
            await response.aread()
            return response


@pytest.mark.smoke
def test_healthcheck_returns_ok() -> None:
    response = asyncio.run(_request("GET", "/api/health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.smoke
def test_root_serves_index() -> None:
    response = asyncio.run(_request("GET", "/"))
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
