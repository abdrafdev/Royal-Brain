from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.relationships.models import Relationship


def get_relationship_by_id(db: Session, *, relationship_id: int) -> Relationship | None:
    return db.get(Relationship, relationship_id)


def list_relationships(
    db: Session, *, as_of: date | None, limit: int
) -> list[Relationship]:
    query = select(Relationship)
    if as_of is not None:
        query = query.where(Relationship.valid_from <= as_of).where(
            (Relationship.valid_to.is_(None)) | (Relationship.valid_to >= as_of)
        )

    query = query.order_by(Relationship.id.desc()).limit(limit)
    return db.scalars(query).all()
