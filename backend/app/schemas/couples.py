from pydantic import BaseModel, Field

from .user import UserPublic


class CouplePreferences(BaseModel):
    tags: list[str] = Field(default_factory=list)
    emotion_goals: list[str] = Field(default_factory=list)
    budget: str = "medium"


class CoupleSummary(BaseModel):
    id: str
    invite_code: str
    members: list[UserPublic]
    preferences: CouplePreferences
    tier: int = Field(default=1, description="커플 티어 (1-5)")
    tier_name: str = Field(default="새싹 커플", description="티어 이름")
    badge_count: int = Field(default=0, description="획득한 배지 개수")


class InviteResponse(BaseModel):
    invite_code: str


class JoinRequest(BaseModel):
    code: str


class PreferenceUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)
    emotion_goals: list[str] = Field(default_factory=list)
    budget: str = "medium"
