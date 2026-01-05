from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.audit.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(
    db: Session = Depends(get_db),
    _admin=Depends(require_roles(Role.ADMIN)),
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "actor_user_id": r.actor_user_id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "occurred_at": r.occurred_at,
            "metadata": r.metadata_,
            "prev_hash": r.prev_hash,
            "event_hash": r.event_hash,
        }
        for r in rows
    ]
