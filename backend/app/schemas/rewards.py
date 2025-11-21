from pydantic import BaseModel


class ChallengeStatus(BaseModel):
    points: int
    badges: list[str]
    challenge_places: list[dict]  # 각 챌린지 장소별 상태 정보





