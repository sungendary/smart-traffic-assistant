from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..dependencies import get_mongo_db
from ..schemas.user import UserPublic
from ..services.users import document_to_user, get_user_by_id
from .security import TokenError, decode_token

http_bearer = HTTPBearer(auto_error=False)


async def get_current_token(credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 필요합니다.")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise TokenError(detail="Access 토큰이 아닙니다.")
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
