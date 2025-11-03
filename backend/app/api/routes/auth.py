from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from ...core.config import settings
from ...core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from ...dependencies import get_mongo_db, get_redis
from ...schemas import auth as auth_schema
from ...schemas.user import UserCreate, UserLogin
from ...services import users as user_service

REFRESH_TOKEN_PREFIX = "auth:refresh:"

router = APIRouter()


@router.post("/signup", response_model=auth_schema.SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> auth_schema.SignupResponse:
    user = await user_service.create_user(db, payload)
    return auth_schema.SignupResponse(user=user)


@router.post("/login", response_model=auth_schema.LoginResponse)
async def login(
    payload: UserLogin,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    redis: Redis = Depends(get_redis),
) -> auth_schema.LoginResponse:
    user_doc = await user_service.authenticate_user(db, payload)
    user = user_service.document_to_user(user_doc)

    access_token, _ = create_access_token(str(user.id), extra={"role": "user"})
    refresh_token, refresh_jti = create_refresh_token(str(user.id))

    refresh_ttl_seconds = settings.refresh_token_expire_minutes * 60
    await redis.set(
        f"{REFRESH_TOKEN_PREFIX}{refresh_jti}",
        str(user.id),
        ex=refresh_ttl_seconds,
    )

    cookie_path = f"{settings.api_prefix}/auth"

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=refresh_ttl_seconds,
        path=cookie_path,
    )

    return auth_schema.LoginResponse(access_token=access_token, user=user)


@router.post("/refresh", response_model=auth_schema.RefreshResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
) -> auth_schema.RefreshResponse:
    if not refresh_token:
        raise TokenError(detail="리프레시 토큰이 없습니다.")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise TokenError(detail="리프레시 토큰이 아닙니다.")

    jti = payload.get("jti")
    cache_key = f"{REFRESH_TOKEN_PREFIX}{jti}" if jti else None
    if not cache_key or not await redis.exists(cache_key):
        raise TokenError(detail="만료되었거나 취소된 리프레시 토큰입니다.")

    subject = payload["sub"]
    access_token, _ = create_access_token(subject, extra={"role": "user"})

    refresh_ttl_seconds = settings.refresh_token_expire_minutes * 60
    cookie_path = f"{settings.api_prefix}/auth"

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=refresh_ttl_seconds,
        path=cookie_path,
    )

    return auth_schema.RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=auth_schema.LogoutResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
) -> auth_schema.LogoutResponse:
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await redis.delete(f"{REFRESH_TOKEN_PREFIX}{jti}")
        except TokenError:
            pass

    response.delete_cookie(key="refresh_token", path=f"{settings.api_prefix}/auth")
    return auth_schema.LogoutResponse()
