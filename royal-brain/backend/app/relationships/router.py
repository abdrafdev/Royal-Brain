from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.families.models import Family
from app.heraldic_entities.models import HeraldicEntity
from app.jurisdictions.models import Jurisdiction
from app.orders.models import Order
from app.persons.models import Person
from app.relationships.models import Relationship
from app.relationships.schemas import (
    ALLOWED_ENTITY_TYPES,
    RelationshipCreate,
    RelationshipRead,
    RelationshipUpdate,
)
from app.relationships.service import get_relationship_by_id, list_relationships
from app.roles.enums import Role
from app.sources.service import get_sources_by_ids
from app.titles.models import Title
from app.users.models import User

router = APIRouter(prefix="/relationships", tags=["relationships"])

ENTITY_MODEL_MAP = {
    "person": Person,
    "family": Family,
    "jurisdiction": Jurisdiction,
    "order": Order,
    "title": Title,
    "heraldic_entity": HeraldicEntity,
}


def _validate_endpoint_exists(db: Session, *, entity_type: str, entity_id: int) -> None:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity_type '{entity_type}'.",
        )

    model = ENTITY_MODEL_MAP[entity_type]
    if db.get(model, entity_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown {entity_type} id: {entity_id}",
        )


@router.get("", response_model=list[RelationshipRead])
def list_relationships_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    as_of: date | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return list_relationships(db, as_of=as_of, limit=limit)


@router.get("/{relationship_id}", response_model=RelationshipRead)
def get_relationship_endpoint(
    relationship_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    obj = get_relationship_by_id(db, relationship_id=relationship_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found"
        )
    return obj


@router.post("", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship_endpoint(
    payload: RelationshipCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    _validate_endpoint_exists(
        db, entity_type=payload.left_entity_type, entity_id=payload.left_entity_id
    )
    _validate_endpoint_exists(
        db, entity_type=payload.right_entity_type, entity_id=payload.right_entity_id
    )

    try:
        sources = get_sources_by_ids(db, source_ids=payload.source_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    data = payload.model_dump(exclude={"source_ids"})
    obj = Relationship(**data)
    obj.sources = sources

    db.add(obj)
    db.flush()

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="CREATE",
            entity_type="relationship",
            entity_id=str(obj.id),
            metadata={"relationship_type": obj.relationship_type, "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{relationship_id}", response_model=RelationshipRead)
def update_relationship_endpoint(
    relationship_id: int,
    payload: RelationshipUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_relationship_by_id(db, relationship_id=relationship_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found"
        )

    # Validate endpoints if they are being changed.
    next_left_type = payload.left_entity_type if payload.left_entity_type is not None else obj.left_entity_type
    next_left_id = payload.left_entity_id if payload.left_entity_id is not None else obj.left_entity_id
    next_right_type = payload.right_entity_type if payload.right_entity_type is not None else obj.right_entity_type
    next_right_id = payload.right_entity_id if payload.right_entity_id is not None else obj.right_entity_id

    _validate_endpoint_exists(db, entity_type=next_left_type, entity_id=next_left_id)
    _validate_endpoint_exists(db, entity_type=next_right_type, entity_id=next_right_id)

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
            entity_type="relationship",
            entity_id=str(obj.id),
            metadata={"fields": sorted(list(updates.keys())), "source_ids": payload.source_ids},
        ),
        commit=False,
    )

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{relationship_id}")
def delete_relationship_endpoint(
    relationship_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    obj = get_relationship_by_id(db, relationship_id=relationship_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found"
        )

    entity_id = obj.id
    db.delete(obj)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor.id,
            action="DELETE",
            entity_type="relationship",
            entity_id=str(entity_id),
            metadata=None,
        ),
        commit=False,
    )

    db.commit()
    return {"ok": True}
