from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

relationship_sources = Table(
    "relationship_sources",
    Base.metadata,
    Column("relationship_id", ForeignKey("relationships.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Free-form string; validation is enforced later by rule engines.
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    left_entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    left_entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    right_entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    right_entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

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

    sources = relationship("Source", secondary=relationship_sources, lazy="selectin")

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
