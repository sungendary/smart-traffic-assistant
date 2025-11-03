from typing import Any

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")


class Place(BaseModel):
    id: str
    name: str
    description: str | None = None
    coordinates: Coordinates
    tags: list[str] = Field(default_factory=list)
    rating: float | None = None
    source: str | None = None

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "Place":
        location = doc.get("location") or {}
        coords = location.get("coordinates", [0, 0])
        longitude, latitude = (coords + [0, 0])[:2]
        return cls(
            id=str(doc.get("_id", "")),
            name=doc.get("name", ""),
            description=doc.get("description"),
            coordinates=Coordinates(latitude=latitude, longitude=longitude),
            tags=list(doc.get("tags", [])),
            rating=doc.get("rating"),
            source=doc.get("source"),
        )
