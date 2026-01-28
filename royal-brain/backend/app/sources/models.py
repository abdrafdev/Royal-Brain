from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # e.g. law, archive, document, decree, registry, ...
    source_type: Mapped[str] = mapped_column("type", String(32), nullable=False)

    # Context jurisdiction for the source itself (where applicable).
    jurisdiction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jurisdictions.id"), nullable=True, index=True
    )

    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Human-readable citation / reference text.
    citation: Mapped[str] = mapped_column(Text, nullable=False)

    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validity interval for this source's asserted effect/applicability.
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

    jurisdiction = relationship("Jurisdiction", back_populates="primary_sources")
