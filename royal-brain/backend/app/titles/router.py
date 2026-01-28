from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.sources.service import get_sources_by_ids
from app.titles.models import Title
from app.titles.schemas import TitleCreate, TitleRead, TitleUpdate
from app.titles.service import get_title_by_id, list_titles
from app.users.models import User

router = APIRouter(prefix="/titles", tags=["titles"])


@router.get("", response_model=list[TitleRead])
def list_titles_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    as_of: date | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return list_titles(db, as_of=as_of, limit=limit)


@router.get("/{title_id}", response_model=TitleRead)
def get_title_endpoint(
    title_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    obj = get_title_by_id(db, title_id=title_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")
    return obj


@router.post("", response_model=TitleRead, status_code=status.HTTP_201_CREATED)
def create_title_endpoint(
    payload: TitleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    try:
        sources = get_sources_by_ids(db, source_ids=payload.source_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    data = payload.model_dump(exclude={"source_ids"})
    obj = Title(**data)
    obj.sources = sources

    db.add(obj)
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="CREATE",
            entity_type="title",
            entity_id=str(obj.id),
            metadata={"name": obj.name, "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{title_id}", response_model=TitleRead)
def update_title_endpoint(
    title_id: int,
    payload: TitleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_title_by_id(db, title_id=title_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

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
            entity_type="title",
            entity_id=str(obj.id),
            metadata={"fields": sorted(list(updates.keys())), "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{title_id}")
def delete_title_endpoint(
    title_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_title_by_id(db, title_id=title_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")

    entity_id = obj.id
    db.delete(obj)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="DELETE",
            entity_type="title",
            entity_id=str(entity_id),
            metadata=None,
        ),
        commit=False,
    )

    db.commit()
    return {"ok": True}
