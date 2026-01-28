from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

heraldic_entity_sources = Table(
    "heraldic_entity_sources",
    Base.metadata,
    Column("heraldic_entity_id", ForeignKey("heraldic_entities.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class HeraldicEntity(Base):
    __tablename__ = "heraldic_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)

    jurisdiction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jurisdictions.id"), nullable=True, index=True
    )

    blazon: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Day 8: Heraldic Intelligence Engine fields
    parsed_structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    svg_cache: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_violations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    jurisdiction_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    jurisdiction_compliance_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_validation_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimant_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=True, index=True
    )

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
    sources = relationship("Source", secondary=heraldic_entity_sources, lazy="selectin")
    claimant = relationship("Person", foreign_keys=[claimant_person_id])

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
