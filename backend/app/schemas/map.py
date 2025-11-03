from pydantic import BaseModel, Field

from .place import Place


class MapSuggestionRequest(BaseModel):
    latitude: float
    longitude: float
    emotion: str = Field(default="joy")
    preferences: list[str] = Field(default_factory=list)
    location_text: str = Field(default="서울")
    additional_context: str | None = None


class MapSuggestionResponse(BaseModel):
    summary: str
    places: list[Place]
    llm_suggestions: list[dict] = Field(default_factory=list)
    llm_task_id: str | None = None
    llm_status: str = "pending"
