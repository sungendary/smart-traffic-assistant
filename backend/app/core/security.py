from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


class TokenError(HTTPException):
    def __init__(self, detail: str = "토큰이 유효하지 않습니다."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_password_hash(password: str) -> str:
    if settings.password_hash_scheme not in pwd_context.schemes():
        raise ValueError(f"지원하지 않는 해시 스킴: {settings.password_hash_scheme}")
    return pwd_context.hash(password, scheme=settings.password_hash_scheme)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str, extra: dict[str, Any] | None = None) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
        "jti": uuid4().hex,
    }
    if extra:
        payload.update(extra)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, payload["jti"]


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> tuple[str, str]:
    return _create_token(subject, timedelta(minutes=settings.access_token_expire_minutes), "access", extra)


def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> tuple[str, str]:
    return _create_token(subject, timedelta(minutes=settings.refresh_token_expire_minutes), "refresh", extra)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:  # pragma: no cover - 다양한 예외 포함
        raise TokenError(detail="토큰 디코딩 실패") from exc
    if "sub" not in payload:
        raise TokenError(detail="토큰에 subject 정보가 없습니다.")
    return payload
