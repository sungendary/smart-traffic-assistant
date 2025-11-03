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


class VisitOut(VisitCreate):
    id: str
    couple_id: str
    user_id: str
    created_at: datetime | None = None
