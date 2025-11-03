from typing import Any

from pydantic import BaseModel


class LLMTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    type: str | None = None
    result: Any | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
