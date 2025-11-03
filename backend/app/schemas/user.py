from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=30)
    preferences: list[str] | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    nickname: str
    email_verified: bool
    created_at: datetime
    preferences: list[str] = Field(default_factory=list)


class UserInDB(BaseModel):
    id: str
    email: EmailStr
    password_hash: str
    nickname: str
    preferences: list[str] | None = None
    email_verified: bool
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
