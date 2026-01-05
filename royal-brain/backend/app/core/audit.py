from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog


@dataclass(frozen=True)
class AuditEvent:
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    metadata: dict[str, Any] | None = None


def compute_event_hash(*, occurred_at: datetime, prev_hash: str | None, event: AuditEvent) -> str:
    payload = {
        "occurred_at": occurred_at.isoformat(),
        "prev_hash": prev_hash,
        "actor_user_id": event.actor_user_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "metadata": event.metadata or {},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def record_audit_event(db: Session, *, event: AuditEvent, commit: bool = True) -> AuditLog:
    occurred_at = datetime.now(timezone.utc)
    prev_hash = db.scalar(select(AuditLog.event_hash).order_by(AuditLog.id.desc()).limit(1))
    event_hash = compute_event_hash(occurred_at=occurred_at, prev_hash=prev_hash, event=event)

    log = AuditLog(
        actor_user_id=event.actor_user_id,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        occurred_at=occurred_at,
        metadata_=event.metadata or None,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )

    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)

    return log
