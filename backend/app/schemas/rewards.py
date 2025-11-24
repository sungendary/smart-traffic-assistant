from pydantic import BaseModel, Field


class ChallengeStatus(BaseModel):
    points: int
    badges: list[str]
    challenge_places: list[dict]  # 각 챌린지 장소별 상태 정보
    tier: int = Field(default=1, description="커플 티어 (1-5)")
    tier_name: str = Field(default="새싹 커플", description="티어 이름")
    badge_count: int = Field(default=0, description="획득한 배지 개수")
    next_tier_badges_needed: int | None = Field(default=None, description="다음 티어까지 필요한 배지 개수")





