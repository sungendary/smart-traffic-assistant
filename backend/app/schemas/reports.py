from pydantic import BaseModel

from .challenges import ChallengeProgress


class ReportResponse(BaseModel):
    month: str
    visit_count: int
    top_tags: list[str]
    emotion_stats: dict[str, int]
    challenge_progress: list[ChallengeProgress]
    summary: str
