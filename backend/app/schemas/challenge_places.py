from datetime import datetime

from pydantic import BaseModel, Field


class ChallengePlaceCreate(BaseModel):
    name: str
    description: str
    latitude: float
    longitude: float
    address: str
    category_id: str  # 카테고리 ID (ObjectId 문자열)
    tags: list[str] = Field(default_factory=list)
    badge_reward: str  # 배지 이모지
    points_reward: int = 500
    active: bool = True


class ChallengePlaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    category_id: str | None = None  # 카테고리 ID (ObjectId 문자열)
    tags: list[str] | None = None
    badge_reward: str | None = None
    points_reward: int | None = None
    active: bool | None = None


class ChallengePlaceOut(BaseModel):
    id: str
    name: str
    description: str
    latitude: float
    longitude: float
    address: str
    category_id: str  # 카테고리 ID (ObjectId 문자열)
    tags: list[str]
    badge_reward: str
    points_reward: int
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None





