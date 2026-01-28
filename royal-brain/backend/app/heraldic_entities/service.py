from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.heraldic_entities.models import HeraldicEntity


def get_heraldic_entity_by_id(
    db: Session, *, heraldic_entity_id: int
) -> HeraldicEntity | None:
    return db.get(HeraldicEntity, heraldic_entity_id)


def list_heraldic_entities(
    db: Session, *, as_of: date | None, limit: int
) -> list[HeraldicEntity]:
    query = select(HeraldicEntity)
    if as_of is not None:
        query = query.where(HeraldicEntity.valid_from <= as_of).where(
            (HeraldicEntity.valid_to.is_(None)) | (HeraldicEntity.valid_to >= as_of)
        )

    query = query.order_by(HeraldicEntity.id.desc()).limit(limit)
    return db.scalars(query).all()
