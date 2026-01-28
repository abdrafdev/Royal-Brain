from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.sources.models import Source


def get_source_by_id(db: Session, *, source_id: int) -> Source | None:
    return db.get(Source, source_id)


def list_sources(db: Session, *, as_of: date | None, limit: int) -> list[Source]:
    query = select(Source)
    if as_of is not None:
        query = query.where(Source.valid_from <= as_of).where(
            (Source.valid_to.is_(None)) | (Source.valid_to >= as_of)
        )

    query = query.order_by(Source.id.desc()).limit(limit)
    return db.scalars(query).all()


def get_sources_by_ids(db: Session, *, source_ids: list[int]) -> list[Source]:
    if not source_ids:
        raise ValueError("At least one source_id is required.")

    unique_ids = sorted(set(source_ids))
    sources = db.scalars(select(Source).where(Source.id.in_(unique_ids))).all()

    if len(sources) != len(unique_ids):
        found = {s.id for s in sources}
        missing = [sid for sid in unique_ids if sid not in found]
        raise ValueError(f"Unknown Source id(s): {missing}")

    sources_by_id = {s.id: s for s in sources}
    return [sources_by_id[sid] for sid in source_ids]
