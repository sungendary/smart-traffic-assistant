from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

from ..core.config import settings

SESSION_KEY_PREFIX = "auth:session:"
USER_SESSIONS_PREFIX = "auth:user-sessions:"


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _user_sessions_key(user_id: str) -> str:
    return f"{USER_SESSIONS_PREFIX}{user_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_ttl() -> int:
    refresh_ttl = settings.refresh_token_expire_minutes * 60
    access_ttl = settings.access_token_expire_minutes * 60
    ttl_candidates = [refresh_ttl, access_ttl, 3600]
    return max(ttl for ttl in ttl_candidates if ttl > 0)


async def _persist(redis: Redis, session: dict[str, Any]) -> dict[str, Any]:
    ttl = _session_ttl()
    key = _session_key(session["session_id"])
    await redis.set(key, json.dumps(session), ex=ttl)
    await redis.sadd(_user_sessions_key(session["user_id"]), session["session_id"])
    await redis.expire(_user_sessions_key(session["user_id"]), ttl)
    return session


async def create_session(
    redis: Redis,
    *,
    session_id: str,
    user_id: str,
    access_jti: str,
    refresh_jti: str,
    user_agent: str | None = None,
    ip: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "last_seen": now,
        "access_jti": access_jti,
        "refresh_jti": refresh_jti,
        "ip": ip,
        "user_agent": user_agent,
    }
    return await _persist(redis, session)


async def get_session(redis: Redis, session_id: str) -> dict[str, Any] | None:
    raw = await redis.get(_session_key(session_id))
    if raw is None:
        return None
    try:
        session = json.loads(raw)
        if isinstance(session, dict):
            return session
    except json.JSONDecodeError:
        return None
    return None


async def update_session(redis: Redis, session_id: str, **fields: Any) -> dict[str, Any] | None:
    session = await get_session(redis, session_id)
    if session is None:
        return None
    session.update(fields)
    session["updated_at"] = _now_iso()
    return await _persist(redis, session)


async def touch_session(
    redis: Redis,
    session_id: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any] | None:
    updates: dict[str, Any] = {"last_seen": _now_iso()}
    if ip is not None:
        updates["ip"] = ip
    if user_agent is not None:
        updates["user_agent"] = user_agent
    return await update_session(redis, session_id, **updates)


async def revoke_session(
    redis: Redis,
    session_id: str,
    *,
    reason: str | None = None,
) -> dict[str, Any] | None:
    session = await get_session(redis, session_id)
    if session is None:
        return None
    session["status"] = "revoked"
    session["revoked_at"] = _now_iso()
    if reason:
        session["revoked_reason"] = reason
    return await _persist(redis, session)


async def delete_session(redis: Redis, session_id: str) -> None:
    session = await get_session(redis, session_id)
    await redis.delete(_session_key(session_id))
    if session:
        await redis.srem(_user_sessions_key(session["user_id"]), session_id)


async def list_sessions(redis: Redis, user_id: str) -> list[dict[str, Any]]:
    key = _user_sessions_key(user_id)
    session_ids = await redis.smembers(key)
    sessions: list[dict[str, Any]] = []
    for session_id in session_ids:
        session = await get_session(redis, session_id)
        if session is None:
            await redis.srem(key, session_id)
            continue
        sessions.append(session)
    return sorted(sessions, key=lambda s: s.get("last_seen", ""), reverse=True)
