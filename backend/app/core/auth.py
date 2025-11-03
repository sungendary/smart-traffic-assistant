from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from ..dependencies import get_mongo_db, get_redis
from ..schemas.user import UserPublic
from ..services.users import document_to_user, get_user_by_id
from ..services import sessions as session_service
from .security import TokenError, decode_token

http_bearer = HTTPBearer(auto_error=False)


async def get_current_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    redis: Redis = Depends(get_redis),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 필요합니다.")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise TokenError(detail="Access 토큰이 아닙니다.")
    session_id = payload.get("session_id")
    if not session_id:
        raise TokenError(detail="세션 정보가 없습니다.")
    session = await session_service.get_session(redis, session_id)
    if session is None or session.get("status") != "active":
        raise TokenError(detail="세션이 만료되었거나 로그아웃되었습니다.")
    if session.get("access_jti") != payload.get("jti"):
        raise TokenError(detail="만료된 토큰입니다.")
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    await session_service.touch_session(redis, session_id, ip=client_ip, user_agent=user_agent)
    return payload


async def get_current_user(
    payload: dict = Depends(get_current_token),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> UserPublic:
    user_id = payload.get("sub")
    if not user_id:
        raise TokenError(detail="토큰에 사용자 정보가 없습니다.")

    doc = await get_user_by_id(db, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")

    return document_to_user(doc)
