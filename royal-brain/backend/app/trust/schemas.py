"""Trust API Schemas — Day 9."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ========== Hash Schemas ==========

class EntityHashResponse(BaseModel):
    """Response model for entity hash."""
    id: int
    entity_type: str
    entity_id: int
    hash_algorithm: str
    hash_value: str
    timestamp: datetime
    computed_by_user_id: int | None


class ComputeHashRequest(BaseModel):
    """Request to compute hash for an entity."""
    entity_type: str = Field(..., description="Type of entity (Person, Title, HeraldicEntity, Order, Family)")
    entity_id: int = Field(..., description="ID of entity to hash")


# ========== Certificate Schemas ==========

class GenerateCertificateRequest(BaseModel):
    """Request to generate verification certificate."""
    entity_type: str
    entity_id: int
    certificate_type: str = Field(default="standard", description="Type of certificate to generate")
    jurisdiction_id: int | None = None
    sources_used: list[dict] | None = None
    rules_applied: list[dict] | None = None
    verification_status: str = Field(default="VALID", description="VALID, INVALID, UNCERTAIN, or PENDING")
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)


class CertificateResponse(BaseModel):
    """Response model for certificate."""
    id: int
    entity_type: str
    entity_id: int
    certificate_type: str
    verification_status: str
    hash_id: int
    certificate_json: dict
    certificate_pdf_path: str | None
    sources_used: dict | None
    rules_applied: dict | None
    jurisdiction_id: int | None
    confidence_score: float | None
    ai_explanation: str | None
    issued_at: datetime
    issued_by_user_id: int
    
    # Relationships
    entity_hash: EntityHashResponse | None = None


# ========== Blockchain Schemas ==========

class AnchorHashRequest(BaseModel):
    """Request to anchor hash(es) to blockchain."""
    hash_ids: list[int] = Field(..., description="List of entity hash IDs to anchor")
    blockchain_network: str = Field(default="polygon-mumbai", description="Blockchain network")
    batch_mode: bool = Field(default=True, description="Use batch anchoring with Merkle tree")


class BlockchainAnchorResponse(BaseModel):
    """Response model for blockchain anchor."""
    id: int
    hash_id: int | None
    merkle_root: str | None
    batch_id: str | None
    blockchain_network: str
    transaction_hash: str
    block_number: int | None
    block_timestamp: datetime | None
    anchor_type: str
    anchored_at: datetime
    explorer_url: str | None


class VerifyAnchorResponse(BaseModel):
    """Response for anchor verification."""
    anchor_id: int
    transaction_hash: str
    blockchain_network: str
    explorer_url: str | None
    verified: bool
    confirmation_status: str
    note: str | None = None


# ========== Combined Verification Response ==========

class FullVerificationResponse(BaseModel):
    """Complete verification info for an entity."""
    entity_type: str
    entity_id: int
    entity_name: str
    current_hash: EntityHashResponse
    certificate: CertificateResponse | None
    blockchain_anchor: BlockchainAnchorResponse | None
    audit_trail: list[dict]


# ========== Audit Trail Schemas ==========

class AuditTrailResponse(BaseModel):
    """Audit trail entry."""
    id: int
    event: str
    entity_type: str | None
    entity_id: int | None
    user_id: int | None
    timestamp: datetime
    metadata: dict | None
    hash_before: str | None
    hash_after: str | None
    verification_certificate_id: int | None
