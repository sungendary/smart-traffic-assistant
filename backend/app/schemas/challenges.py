from pydantic import BaseModel


class ChallengeProgress(BaseModel):
    id: str
    title: str
    description: str
    badge_icon: str
    current: int
    goal: int
    completed: bool
    completed_at: str | None
