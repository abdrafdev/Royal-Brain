from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persons.models import Person


def get_person_by_id(db: Session, *, person_id: int) -> Person | None:
    return db.get(Person, person_id)


def list_persons(db: Session, *, as_of: date | None, limit: int) -> list[Person]:
    query = select(Person)
    if as_of is not None:
        query = query.where(Person.valid_from <= as_of).where(
            (Person.valid_to.is_(None)) | (Person.valid_to >= as_of)
        )

    query = query.order_by(Person.id.desc()).limit(limit)
    return db.scalars(query).all()
