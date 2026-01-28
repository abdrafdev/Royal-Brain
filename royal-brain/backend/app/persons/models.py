from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

person_sources = Table(
    "person_sources",
    Base.metadata,
    Column("person_id", ForeignKey("persons.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Baseline human-readable name.
    primary_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # Sex/Gender marker (e.g., M, F, X, UNKNOWN). Optional for backward compatibility.
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Multiple names over time (each element is a dict with its own valid_from/valid_to).
    names: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    death_date: Mapped[date | None] = mapped_column(Date, nullable=True)

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

    sources = relationship("Source", secondary=person_sources, lazy="selectin")

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
