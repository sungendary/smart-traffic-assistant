from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .place import Place


class MapSuggestionRequest(BaseModel):
    latitude: float
    longitude: float
    emotion: str = Field(default="joy")
    preferences: list[str] = Field(default_factory=list)
    location_text: str = Field(default="서울")
    additional_context: str | None = None
    budget: Optional[str] = Field(default=None, description="예산 범위 (예: 5만원 이하)")
    date: Optional[date] = Field(default=None, description="데이트 날짜 (YYYY-MM-DD)")


class MapSuggestionResponse(BaseModel):
    summary: str
    places: list[Place]
    llm_suggestions: list[dict]
