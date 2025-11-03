from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SessionInfo(BaseModel):
    session_id: str
    status: Literal["active", "revoked", "unknown"]
    created_at: datetime | None
    last_seen: datetime | None
    ip: str | None = None
    user_agent: str | None = None
    is_current: bool = False
