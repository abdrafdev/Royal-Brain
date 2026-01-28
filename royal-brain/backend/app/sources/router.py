from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.sources.models import Source
from app.sources.schemas import SourceCreate, SourceRead, SourceUpdate
from app.sources.service import get_source_by_id, list_sources
from app.users.models import User

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
def list_sources_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    as_of: date | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return list_sources(db, as_of=as_of, limit=limit)


@router.get("/{source_id}", response_model=SourceRead)
def get_source_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    source = get_source_by_id(db, source_id=source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    source = Source(**payload.model_dump())
    db.add(source)
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="CREATE",
            entity_type="source",
            entity_id=str(source.id),
            metadata={"type": source.source_type},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceRead)
def update_source_endpoint(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    source = get_source_by_id(db, source_id=source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(source, field, value)

    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="UPDATE",
            entity_type="source",
            entity_id=str(source.id),
            metadata={"fields": sorted(list(updates.keys()))},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    source = get_source_by_id(db, source_id=source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    entity_id = source.id
    db.delete(source)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="DELETE",
            entity_type="source",
            entity_id=str(entity_id),
            metadata=None,
        ),
        commit=False,
    )

    db.commit()
    return {"ok": True}
