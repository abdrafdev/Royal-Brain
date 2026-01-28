from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.families.models import Family


def get_family_by_id(db: Session, *, family_id: int) -> Family | None:
    return db.get(Family, family_id)


def list_families(db: Session, *, as_of: date | None, limit: int) -> list[Family]:
    query = select(Family)
    if as_of is not None:
        query = query.where(Family.valid_from <= as_of).where(
            (Family.valid_to.is_(None)) | (Family.valid_to >= as_of)
        )

    query = query.order_by(Family.id.desc()).limit(limit)
    return db.scalars(query).all()
