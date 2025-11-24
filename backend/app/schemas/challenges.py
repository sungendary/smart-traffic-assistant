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


class LocationVerifyRequest(BaseModel):
    challenge_place_id: str
    latitude: float
    longitude: float


class LocationVerifyResponse(BaseModel):
    verified: bool
    distance_meters: float
    message: str