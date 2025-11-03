from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from ...core.auth import get_current_token, get_current_user, http_bearer
from ...core.config import settings
from ...core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from ...dependencies import get_mongo_db, get_redis
from ...schemas import (
    LoginResponse,
    RefreshResponse,
    SignupResponse,
    SessionInfo,
    UserPublic,
)
from ...schemas.user import UserCreate, UserLogin
from ...services import sessions as session_service
from ...services import users as user_service

REFRESH_PREFIX = "auth:refresh:"

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> SignupResponse:
    user = await user_service.create_user(db, payload)
    return SignupResponse(user=user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    redis: Redis = Depends(get_redis),
) -> LoginResponse:
    user_doc = await user_service.authenticate_user(db, payload)
    user = user_service.document_to_user(user_doc)

    session_id = uuid4().hex
    access_token, access_jti = create_access_token(
        str(user.id),
        extra={"role": "user", "session_id": session_id},
    )
    refresh_token, refresh_jti = create_refresh_token(
        str(user.id),
        extra={"session_id": session_id},
    )

    ttl = settings.refresh_token_expire_minutes * 60
    await redis.set(f"{REFRESH_PREFIX}{refresh_jti}", str(user.id), ex=ttl)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await session_service.create_session(
        redis,
        session_id=session_id,
        user_id=str(user.id),
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        ip=client_ip,
        user_agent=user_agent,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=ttl,
        path=f"{settings.api_prefix}/auth",
    )

    return LoginResponse(access_token=access_token, user=user)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
) -> RefreshResponse:
    if not refresh_token:
        raise TokenError(detail="리프레시 토큰이 없습니다.")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise TokenError(detail="리프레시 토큰이 아닙니다.")

    session_id = payload.get("session_id")
    if not session_id:
        raise TokenError(detail="세션 정보가 없습니다.")

    jti = payload.get("jti")
    cache_key = f"{REFRESH_PREFIX}{jti}" if jti else None
    if not cache_key or not await redis.exists(cache_key):
        raise TokenError(detail="만료되었거나 취소된 리프레시 토큰입니다.")

    session = await session_service.get_session(redis, session_id)
    if session is None or session.get("status") != "active":
        raise TokenError(detail="세션이 만료되었거나 존재하지 않습니다.")
    if session.get("refresh_jti") != jti:
        raise TokenError(detail="토큰이 교체되었습니다. 다시 로그인해 주세요.")

    await redis.delete(cache_key)

    ttl = settings.refresh_token_expire_minutes * 60

    new_refresh_token, new_refresh_jti = create_refresh_token(
        payload["sub"],
        extra={"session_id": session_id},
    )
    await redis.set(f"{REFRESH_PREFIX}{new_refresh_jti}", str(payload["sub"]), ex=ttl)

    access_token, access_jti = create_access_token(
        payload["sub"],
        extra={"role": "user", "session_id": session_id},
    )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await session_service.update_session(
        redis,
        session_id,
        access_jti=access_jti,
        refresh_jti=new_refresh_jti,
    )
    await session_service.touch_session(redis, session_id, ip=client_ip, user_agent=user_agent)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=ttl,
        path=f"{settings.api_prefix}/auth",
    )
    return RefreshResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> dict:
    session_id: str | None = None
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") == "refresh":
                session_id = payload.get("session_id")
                jti = payload.get("jti")
                if jti:
                    await redis.delete(f"{REFRESH_PREFIX}{jti}")
        except TokenError:
            pass
    if session_id is None and credentials:
        try:
            access_payload = decode_token(credentials.credentials)
            if access_payload.get("type") == "access":
                session_id = access_payload.get("session_id")
        except TokenError:
            session_id = None
    response.delete_cookie(key="refresh_token", path=f"{settings.api_prefix}/auth")
    if session_id:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await session_service.touch_session(redis, session_id, ip=client_ip, user_agent=user_agent)
        await session_service.revoke_session(redis, session_id, reason="logout")
    return {"message": "로그아웃되었습니다."}


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    token_payload: dict = Depends(get_current_token),
    redis: Redis = Depends(get_redis),
) -> list[SessionInfo]:
    user_id = token_payload["sub"]
    current_session_id = token_payload.get("session_id")
    sessions = await session_service.list_sessions(redis, user_id)
    return [
        SessionInfo(
            session_id=session["session_id"],
            status=session.get("status", "unknown"),
            created_at=session.get("created_at"),
            last_seen=session.get("last_seen"),
            ip=session.get("ip"),
            user_agent=session.get("user_agent"),
            is_current=session["session_id"] == current_session_id,
        )
        for session in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    token_payload: dict = Depends(get_current_token),
    redis: Redis = Depends(get_redis),
) -> Response:
    session = await session_service.get_session(redis, session_id)
    if session is None or session.get("user_id") != token_payload["sub"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    await session_service.revoke_session(redis, session_id, reason="user_revoked")
    refresh_jti = session.get("refresh_jti")
    if refresh_jti:
        await redis.delete(f"{REFRESH_PREFIX}{refresh_jti}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
