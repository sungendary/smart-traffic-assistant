from fastapi import APIRouter, Cookie, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from ...core.auth import get_current_user
from ...core.config import settings
from ...core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from ...dependencies import get_mongo_db, get_redis
from ...schemas import LoginResponse, RefreshResponse, SignupResponse, UserPublic
from ...schemas.user import UserCreate, UserLogin
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
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    redis: Redis = Depends(get_redis),
) -> LoginResponse:
    user_doc = await user_service.authenticate_user(db, payload)
    user = user_service.document_to_user(user_doc)

    access_token, _ = create_access_token(str(user.id), extra={"role": "user"})
    refresh_token, refresh_jti = create_refresh_token(str(user.id))

    ttl = settings.refresh_token_expire_minutes * 60
    await redis.set(f"{REFRESH_PREFIX}{refresh_jti}", str(user.id), ex=ttl)

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
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
) -> RefreshResponse:
    if not refresh_token:
        raise TokenError(detail="리프레시 토큰이 없습니다.")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise TokenError(detail="리프레시 토큰이 아닙니다.")

    jti = payload.get("jti")
    cache_key = f"{REFRESH_PREFIX}{jti}" if jti else None
    if not cache_key or not await redis.exists(cache_key):
        raise TokenError(detail="만료되었거나 취소된 리프레시 토큰입니다.")

    access_token, _ = create_access_token(payload["sub"], extra={"role": "user"})
    ttl = settings.refresh_token_expire_minutes * 60
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=ttl,
        path=f"{settings.api_prefix}/auth",
    )
    return RefreshResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    redis: Redis = Depends(get_redis),
) -> dict:
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await redis.delete(f"{REFRESH_PREFIX}{jti}")
        except TokenError:
            pass
    response.delete_cookie(key="refresh_token", path=f"{settings.api_prefix}/auth")
    return {"message": "로그아웃되었습니다."}


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
