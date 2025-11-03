from datetime import date as Date

from pydantic import BaseModel, Field


class PlanStop(BaseModel):
    place_id: str
    place_name: str | None = None
    note: str | None = None
    expected_time: str | None = None
    order: int = 0


class PlanCreate(BaseModel):
    title: str
    date: Date | None = None
    emotion_goal: str | None = None
    budget_range: str | None = None
    notes: str | None = None
    stops: list[PlanStop] = Field(default_factory=list)


class PlanUpdate(BaseModel):
    title: str | None = None
    date: Date | None = None
    emotion_goal: str | None = None
    budget_range: str | None = None
    notes: str | None = None
    stops: list[PlanStop] | None = None


class PlanOut(BaseModel):
    id: str
    couple_id: str
    title: str
    date: str | None = None
    emotion_goal: str | None = None
    budget_range: str | None = None
    notes: str | None = None
    stops: list[PlanStop] = Field(default_factory=list)
