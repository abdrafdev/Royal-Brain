from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.heraldic_entities.models import HeraldicEntity
from app.heraldic_entities.schemas import (
    HeraldicEntityCreate,
    HeraldicEntityRead,
    HeraldicEntityUpdate,
)
from app.heraldic_entities.service import get_heraldic_entity_by_id, list_heraldic_entities
from app.roles.enums import Role
from app.sources.service import get_sources_by_ids
from app.users.models import User

router = APIRouter(prefix="/heraldic-entities", tags=["heraldic-entities"])


@router.get("", response_model=list[HeraldicEntityRead])
def list_heraldic_entities_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    as_of: date | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return list_heraldic_entities(db, as_of=as_of, limit=limit)


@router.get("/{heraldic_entity_id}", response_model=HeraldicEntityRead)
def get_heraldic_entity_endpoint(
    heraldic_entity_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    obj = get_heraldic_entity_by_id(db, heraldic_entity_id=heraldic_entity_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Heraldic entity not found"
        )
    return obj


@router.post("", response_model=HeraldicEntityRead, status_code=status.HTTP_201_CREATED)
def create_heraldic_entity_endpoint(
    payload: HeraldicEntityCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    try:
        sources = get_sources_by_ids(db, source_ids=payload.source_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    data = payload.model_dump(exclude={"source_ids"})
    obj = HeraldicEntity(**data)
    obj.sources = sources

    db.add(obj)
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="CREATE",
            entity_type="heraldic_entity",
            entity_id=str(obj.id),
            metadata={"name": obj.name, "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{heraldic_entity_id}", response_model=HeraldicEntityRead)
def update_heraldic_entity_endpoint(
    heraldic_entity_id: int,
    payload: HeraldicEntityUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_heraldic_entity_by_id(db, heraldic_entity_id=heraldic_entity_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Heraldic entity not found"
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
            entity_type="heraldic_entity",
            entity_id=str(obj.id),
            metadata={
                "fields": sorted(list(updates.keys())),
                "source_ids": payload.source_ids,
            },
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{heraldic_entity_id}")
def delete_heraldic_entity_endpoint(
    heraldic_entity_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_heraldic_entity_by_id(db, heraldic_entity_id=heraldic_entity_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Heraldic entity not found"
        )

    entity_id = obj.id
    db.delete(obj)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="DELETE",
            entity_type="heraldic_entity",
            entity_id=str(entity_id),
            metadata=None,
        ),
        commit=False,
    )

    db.commit()
    return {"ok": True}
