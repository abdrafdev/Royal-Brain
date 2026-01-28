from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jurisdictions.models import Jurisdiction


def get_jurisdiction_by_id(db: Session, *, jurisdiction_id: int) -> Jurisdiction | None:
    return db.get(Jurisdiction, jurisdiction_id)


def list_jurisdictions(
    db: Session, *, as_of: date | None, limit: int
) -> list[Jurisdiction]:
    query = select(Jurisdiction)
    if as_of is not None:
        query = query.where(Jurisdiction.valid_from <= as_of).where(
            (Jurisdiction.valid_to.is_(None)) | (Jurisdiction.valid_to >= as_of)
        )

    query = query.order_by(Jurisdiction.id.desc()).limit(limit)
    return db.scalars(query).all()
