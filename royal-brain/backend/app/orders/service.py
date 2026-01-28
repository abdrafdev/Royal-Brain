from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orders.models import Order


def get_order_by_id(db: Session, *, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def list_orders(db: Session, *, as_of: date | None, limit: int) -> list[Order]:
    query = select(Order)
    if as_of is not None:
        query = query.where(Order.valid_from <= as_of).where(
            (Order.valid_to.is_(None)) | (Order.valid_to >= as_of)
        )

    query = query.order_by(Order.id.desc()).limit(limit)
    return db.scalars(query).all()
