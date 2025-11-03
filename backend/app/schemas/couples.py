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


class InviteResponse(BaseModel):
    invite_code: str


class JoinRequest(BaseModel):
    code: str


class PreferenceUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)
    emotion_goals: list[str] = Field(default_factory=list)
    budget: str = "medium"
