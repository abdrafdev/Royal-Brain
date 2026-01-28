from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.jurisdictions.models import Jurisdiction
from app.jurisdictions.schemas import JurisdictionCreate, JurisdictionRead, JurisdictionUpdate
from app.jurisdictions.service import get_jurisdiction_by_id, list_jurisdictions
from app.roles.enums import Role
from app.sources.service import get_sources_by_ids
from app.users.models import User

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])


@router.get("", response_model=list[JurisdictionRead])
def list_jurisdictions_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    as_of: date | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return list_jurisdictions(db, as_of=as_of, limit=limit)


@router.get("/{jurisdiction_id}", response_model=JurisdictionRead)
def get_jurisdiction_endpoint(
    jurisdiction_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    obj = get_jurisdiction_by_id(db, jurisdiction_id=jurisdiction_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )
    return obj


@router.post("", response_model=JurisdictionRead, status_code=status.HTTP_201_CREATED)
def create_jurisdiction_endpoint(
    payload: JurisdictionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    try:
        sources = get_sources_by_ids(db, source_ids=payload.source_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    data = payload.model_dump(exclude={"source_ids"})
    obj = Jurisdiction(**data)
    obj.sources = sources

    db.add(obj)
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="CREATE",
            entity_type="jurisdiction",
            entity_id=str(obj.id),
            metadata={"name": obj.name, "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{jurisdiction_id}", response_model=JurisdictionRead)
def update_jurisdiction_endpoint(
    jurisdiction_id: int,
    payload: JurisdictionUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_jurisdiction_by_id(db, jurisdiction_id=jurisdiction_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )

    try:
        sources = get_sources_by_ids(db, source_ids=payload.source_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    updates = payload.model_dump(exclude_unset=True, exclude={"source_ids"})
    for field, value in updates.items():
        setattr(obj, field, value)

    obj.sources = sources
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="UPDATE",
            entity_type="jurisdiction",
            entity_id=str(obj.id),
            metadata={"fields": sorted(list(updates.keys())), "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{jurisdiction_id}")
def delete_jurisdiction_endpoint(
    jurisdiction_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_jurisdiction_by_id(db, jurisdiction_id=jurisdiction_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found"
        )

    entity_id = obj.id
    db.delete(obj)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="DELETE",
            entity_type="jurisdiction",
            entity_id=str(entity_id),
            metadata=None,
        ),
        commit=False,
    )

    db.commit()
    return {"ok": True}
