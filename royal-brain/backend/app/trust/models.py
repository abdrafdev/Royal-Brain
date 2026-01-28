"""Trust & Certification Layer — Day 9 Database Models.

Cryptographic hashing, verification certificates, blockchain anchoring.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EntityHash(Base):
    """Cryptographic hash of entity for integrity verification."""
    
    __tablename__ = "entity_hashes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hash_algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    hash_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    computed_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    
    computed_by = relationship("User", foreign_keys=[computed_by_user_id])
    
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "timestamp", name="uq_entity_hash_version"),
    )


class VerificationCertificate(Base):
    """Verification certificate for validated entities."""
    
    __tablename__ = "verification_certificates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    certificate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    hash_id: Mapped[int] = mapped_column(Integer, ForeignKey("entity_hashes.id"), nullable=False)
    certificate_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    certificate_pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sources_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules_applied: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    jurisdiction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jurisdictions.id"), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    issued_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    entity_hash = relationship("EntityHash", foreign_keys=[hash_id])
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])
    issued_by = relationship("User", foreign_keys=[issued_by_user_id])


class BlockchainAnchor(Base):
    """Blockchain anchoring proof for immutable timestamping."""
    
    __tablename__ = "blockchain_anchors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hash_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("entity_hashes.id"), nullable=True)
    merkle_root: Mapped[str | None] = mapped_column(String(128), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    blockchain_network: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anchor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    anchored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    anchored_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    explorer_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    entity_hash = relationship("EntityHash", foreign_keys=[hash_id])
    anchored_by = relationship("User", foreign_keys=[anchored_by_user_id])
