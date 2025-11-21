from datetime import datetime

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    plan_id: str | None = None
    place_id: str
    place_name: str | None = None
    visited_at: str | None = None
    emotion: str | None = None
    tags: list[str] = Field(default_factory=list)
    memo: str | None = None
    rating: float | None = None
    challenge_place_id: str | None = None  # 챌린지 장소 ID
    location_verified: bool = False  # 위치 인증 완료 여부


class VisitOut(VisitCreate):
    id: str
    couple_id: str
    user_id: str
    review_completed: bool = False  # 리뷰 및 별점 작성 완료 여부
    created_at: datetime | None = None
