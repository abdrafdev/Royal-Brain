from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

jurisdiction_sources = Table(
    "jurisdiction_sources",
    Base.metadata,
    Column("jurisdiction_id", ForeignKey("jurisdictions.id"), primary_key=True),
    Column("source_id", ForeignKey("sources.id"), primary_key=True),
)


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)

    legal_system: Mapped[str | None] = mapped_column(String(64), nullable=True)

    nobility_abolished_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # JSON payload storing jurisdiction-specific rules for the engines (including succession parameters).
    succession_rules_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # JSON list of order names/identifiers recognized by the jurisdiction.
    recognized_orders: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # JSON list of legal reference strings.
    legal_references: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    jurisdiction_type: Mapped[str | None] = mapped_column("type", String(64), nullable=True)

    parent_id: Mapped[int | None] = mapped_column(
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

    parent = relationship("Jurisdiction", remote_side="Jurisdiction.id", back_populates="children")
    children = relationship("Jurisdiction", back_populates="parent")

    # Sources whose own context jurisdiction points at this jurisdiction.
    primary_sources = relationship("Source", back_populates="jurisdiction")

    # Evidentiary sources supporting this jurisdiction record.
    sources = relationship("Source", secondary=jurisdiction_sources, lazy="selectin")

    @property
    def source_ids(self) -> list[int]:
        return [s.id for s in self.sources]
