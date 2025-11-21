from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field

from .place import Place


class MapSuggestionRequest(BaseModel):
    latitude: float
    longitude: float
    emotion: str = Field(default="joy")
    preferences: list[str] = Field(default_factory=list)
    location_text: str = Field(default="서울")
    additional_context: str | None = None
    budget: Optional[str] = None
    date: Optional[date] = None


class MapSuggestionResponse(BaseModel):
    summary: str
    places: list[Place]
    llm_suggestions: list[dict[str, Any]]
