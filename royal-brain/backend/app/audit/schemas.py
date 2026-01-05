from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    occurred_at: datetime
    metadata: dict[str, Any] | None
    prev_hash: str | None
    event_hash: str
