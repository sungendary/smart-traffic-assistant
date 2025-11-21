<<<<<<< Updated upstream
=======
from datetime import datetime
from typing import Optional

>>>>>>> Stashed changes
from pydantic import BaseModel, Field

from .challenges import ChallengeProgress


class ReportResponse(BaseModel):
    month: str
    visit_count: int
    top_tags: list[str]
    emotion_stats: dict[str, int]
    challenge_progress: list[ChallengeProgress]
    preferred_tags: list[str] = Field(default_factory=list)
    preferred_emotion_goals: list[str] = Field(default_factory=list)
    plan_emotion_goals: list[str] = Field(default_factory=list)
    summary: str


class SavedReport(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    couple_id: str
    month: str
    visit_count: int
    top_tags: list[str]
    emotion_stats: dict[str, int]
    challenge_progress: list[ChallengeProgress]
    summary: str
    created_at: datetime
    updated_at: datetime
