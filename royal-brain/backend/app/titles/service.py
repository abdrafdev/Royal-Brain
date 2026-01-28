from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.titles.models import Title


def get_title_by_id(db: Session, *, title_id: int) -> Title | None:
    return db.get(Title, title_id)


def list_titles(db: Session, *, as_of: date | None, limit: int) -> list[Title]:
    query = select(Title)
    if as_of is not None:
        query = query.where(Title.valid_from <= as_of).where(
            (Title.valid_to.is_(None)) | (Title.valid_to >= as_of)
        )

    query = query.order_by(Title.id.desc()).limit(limit)
    return db.scalars(query).all()
