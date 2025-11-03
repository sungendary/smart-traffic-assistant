from datetime import datetime

from pydantic import BaseModel

from .user import UserPublic


class SignupResponse(BaseModel):
    user: UserPublic


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "로그아웃 되었습니다"
    timestamp: datetime = datetime.utcnow()
