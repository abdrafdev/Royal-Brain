from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

title_sources = Table(
    "title_sources",
    Base.metadata,
    Column("title_id", ForeignKey("titles.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Title(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Historical grant context (optional, required for succession validation back to a grantor).
    granted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    grantor_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=True, index=True
    )

    jurisdiction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jurisdictions.id"), nullable=True, index=True
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
    sources = relationship("Source", secondary=title_sources, lazy="selectin")

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
