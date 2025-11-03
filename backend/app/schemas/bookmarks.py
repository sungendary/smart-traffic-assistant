from datetime import datetime

from pydantic import BaseModel, Field


class BookmarkCreate(BaseModel):
    place_id: str
    place_name: str | None = None
    address: str | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class BookmarkOut(BookmarkCreate):
    id: str
    couple_id: str
    user_id: str
    created_at: datetime | None = None
