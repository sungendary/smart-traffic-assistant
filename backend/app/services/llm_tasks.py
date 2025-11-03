from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi import HTTPException, status

from ..db.redis import RedisConnectionManager
from .llm import generate_itinerary_suggestions, generate_report_summary


class LLMTaskType(str, Enum):
    ITINERARY = "itinerary"
    REPORT = "report"


TASK_KEY_PREFIX = "llm:task:"
TASK_TTL_SECONDS = 60 * 60  # 1 hour


async def _write_task_state(task_id: str, data: dict[str, Any]) -> None:
    client = RedisConnectionManager.get_client()
    mapping = {key: json.dumps(value) if isinstance(value, (dict, list)) else str(value) for key, value in data.items()}
    await client.hset(f"{TASK_KEY_PREFIX}{task_id}", mapping=mapping)
    await client.expire(f"{TASK_KEY_PREFIX}{task_id}", TASK_TTL_SECONDS)


async def _run_task(task_id: str, task_type: LLMTaskType, payload: dict[str, Any]) -> None:
    await _write_task_state(
        task_id,
        {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    task_fn: Callable[[dict[str, Any]], Awaitable[Any]]
    if task_type is LLMTaskType.ITINERARY:
        task_fn = generate_itinerary_suggestions
    elif task_type is LLMTaskType.REPORT:
        task_fn = generate_report_summary
    else:  # pragma: no cover
        await _write_task_state(
            task_id,
            {
                "status": "failed",
                "error": f"Unsupported LLM task type: {task_type}",
            },
        )
        return

    try:
        result = await task_fn(payload)
    except Exception as exc:  # pragma: no cover
        await _write_task_state(
            task_id,
            {
                "status": "failed",
                "error": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    await _write_task_state(
        task_id,
        {
            "status": "completed",
            "result": result,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def enqueue_llm_task(task_type: LLMTaskType, payload: dict[str, Any]) -> str:
    task_id = uuid4().hex
    await _write_task_state(
        task_id,
        {
            "status": "pending",
            "type": task_type.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    asyncio.create_task(_run_task(task_id, task_type, payload))
    return task_id


async def get_task_status(task_id: str) -> dict[str, Any]:
    client = RedisConnectionManager.get_client()
    raw = await client.hgetall(f"{TASK_KEY_PREFIX}{task_id}")
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    data: dict[str, Any] = {}
    for key, value in raw.items():
        try:
            data[key] = json.loads(value)
        except json.JSONDecodeError:
            data[key] = value
    data["task_id"] = task_id
    return data


async def clear_task(task_id: str) -> None:
    client = RedisConnectionManager.get_client()
    await client.delete(f"{TASK_KEY_PREFIX}{task_id}")
