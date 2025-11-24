from datetime import datetime

from pydantic import BaseModel


class ChallengeCategoryCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None  # 카테고리 아이콘 이모지
    color: str | None = None  # UI 테마 컬러 (HEX)
    active: bool = True


class ChallengeCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    active: bool | None = None


class ChallengeCategoryOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

