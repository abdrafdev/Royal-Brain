from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

order_sources = Table(
    "order_sources",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)

    jurisdiction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jurisdictions.id"), nullable=True, index=True
    )

    # Day 7: Legitimacy engine fields
    classification: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legitimacy_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fons_honorum_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=True, index=True
    )
    fraud_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recognized_by: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    founding_document_source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sources.id"), nullable=True, index=True
    )
    last_legitimacy_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    granted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    grantor_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=True, index=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    jurisdiction = relationship("Jurisdiction")
    sources = relationship("Source", secondary=order_sources, lazy="selectin")

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
