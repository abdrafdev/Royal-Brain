"""Trust API Router — Day 9.

Endpoints for cryptographic verification, certificates, and blockchain anchoring.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.core.authority import require_roles
from app.core.audit import AuditEvent, record_audit_event
from app.core.database import get_db
from app.roles.enums import Role
from app.trust.blockchain import anchor_single_hash, anchor_batch_hashes, get_anchor_for_hash, verify_anchor
from app.trust.certificates import generate_certificate, get_certificate, get_certificates_for_entity, VerificationStatus
from app.trust.hashing import hash_person, hash_title, hash_heraldic_entity, hash_order, hash_family, get_latest_hash, verify_hash
from app.trust.schemas import (
    ComputeHashRequest,
    EntityHashResponse,
    GenerateCertificateRequest,
    CertificateResponse,
    AnchorHashRequest,
    BlockchainAnchorResponse,
    VerifyAnchorResponse,
    FullVerificationResponse,
    AuditTrailResponse,
)
from app.users.models import User

router = APIRouter(prefix="/api/v1/trust", tags=["trust"])


# ========== Hash Endpoints ==========

@router.post("/hash", response_model=EntityHashResponse)
def compute_entity_hash(
    payload: ComputeHashRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
) -> EntityHashResponse:
    """Compute cryptographic hash for an entity.
    
    RBAC: ADMIN, RESEARCHER
    """
    
    # Compute hash based on entity type
    if payload.entity_type == "Person":
        entity_hash = hash_person(db, payload.entity_id, user_id=current_user.id)
    elif payload.entity_type == "Title":
        entity_hash = hash_title(db, payload.entity_id, user_id=current_user.id)
    elif payload.entity_type == "HeraldicEntity":
        entity_hash = hash_heraldic_entity(db, payload.entity_id, user_id=current_user.id)
    elif payload.entity_type == "Order":
        entity_hash = hash_order(db, payload.entity_id, user_id=current_user.id)
    elif payload.entity_type == "Family":
        entity_hash = hash_family(db, payload.entity_id, user_id=current_user.id)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {payload.entity_type}")
    
    # Record audit event
    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=current_user.id,
            action="HASH_COMPUTED",
            entity_type=payload.entity_type,
            entity_id=str(payload.entity_id),
            metadata={"hash_id": entity_hash.id, "hash_value": entity_hash.hash_value},
        ),
        commit=True,
    )
    
    return EntityHashResponse(
        id=entity_hash.id,
        entity_type=entity_hash.entity_type,
        entity_id=entity_hash.entity_id,
        hash_algorithm=entity_hash.hash_algorithm,
        hash_value=entity_hash.hash_value,
        timestamp=entity_hash.timestamp,
        computed_by_user_id=entity_hash.computed_by_user_id,
    )


@router.get("/hash/{entity_type}/{entity_id}", response_model=EntityHashResponse)
def get_entity_hash(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> EntityHashResponse:
    """Get latest hash for an entity.
    
    RBAC: All authenticated users
    """
    
    entity_hash = get_latest_hash(db, entity_type, entity_id)
    if not entity_hash:
        raise HTTPException(status_code=404, detail="No hash found for this entity")
    
    return EntityHashResponse(
        id=entity_hash.id,
        entity_type=entity_hash.entity_type,
        entity_id=entity_hash.entity_id,
        hash_algorithm=entity_hash.hash_algorithm,
        hash_value=entity_hash.hash_value,
        timestamp=entity_hash.timestamp,
        computed_by_user_id=entity_hash.computed_by_user_id,
    )


# ========== Certificate Endpoints ==========

@router.post("/certificate", response_model=CertificateResponse)
def create_certificate(
    payload: GenerateCertificateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
) -> CertificateResponse:
    """Generate verification certificate for an entity.
    
    RBAC: ADMIN, RESEARCHER
    """
    
    try:
        status = VerificationStatus(payload.verification_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid verification status: {payload.verification_status}")
    
    certificate = generate_certificate(
        db,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        certificate_type=payload.certificate_type,
        user_id=current_user.id,
        jurisdiction_id=payload.jurisdiction_id,
        sources_used=payload.sources_used,
        rules_applied=payload.rules_applied,
        verification_status=status,
        confidence_score=payload.confidence_score,
    )
    
    # Record audit event
    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=current_user.id,
            action="CERTIFICATE_ISSUED",
            entity_type=payload.entity_type,
            entity_id=str(payload.entity_id),
            metadata={"certificate_id": certificate.id, "status": certificate.verification_status},
        ),
        commit=True,
    )
    
    return CertificateResponse(
        id=certificate.id,
        entity_type=certificate.entity_type,
        entity_id=certificate.entity_id,
        certificate_type=certificate.certificate_type,
        verification_status=certificate.verification_status,
        hash_id=certificate.hash_id,
        certificate_json=certificate.certificate_json,
        certificate_pdf_path=certificate.certificate_pdf_path,
        sources_used=certificate.sources_used,
        rules_applied=certificate.rules_applied,
        jurisdiction_id=certificate.jurisdiction_id,
        confidence_score=certificate.confidence_score,
        ai_explanation=certificate.ai_explanation,
        issued_at=certificate.issued_at,
        issued_by_user_id=certificate.issued_by_user_id,
    )


@router.get("/certificate/{certificate_id}", response_model=CertificateResponse)
def get_certificate_endpoint(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> CertificateResponse:
    """Retrieve certificate by ID.
    
    RBAC: All authenticated users
    """
    
    certificate = get_certificate(db, certificate_id)
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return CertificateResponse(
        id=certificate.id,
        entity_type=certificate.entity_type,
        entity_id=certificate.entity_id,
        certificate_type=certificate.certificate_type,
        verification_status=certificate.verification_status,
        hash_id=certificate.hash_id,
        certificate_json=certificate.certificate_json,
        certificate_pdf_path=certificate.certificate_pdf_path,
        sources_used=certificate.sources_used,
        rules_applied=certificate.rules_applied,
        jurisdiction_id=certificate.jurisdiction_id,
        confidence_score=certificate.confidence_score,
        ai_explanation=certificate.ai_explanation,
        issued_at=certificate.issued_at,
        issued_by_user_id=certificate.issued_by_user_id,
    )


@router.get("/certificates/{entity_type}/{entity_id}", response_model=list[CertificateResponse])
def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> list[CertificateResponse]:
    """Get all certificates for an entity.
    
    RBAC: All authenticated users
    """
    
    certificates = get_certificates_for_entity(db, entity_type, entity_id)
    
    return [
        CertificateResponse(
            id=cert.id,
            entity_type=cert.entity_type,
            entity_id=cert.entity_id,
            certificate_type=cert.certificate_type,
            verification_status=cert.verification_status,
            hash_id=cert.hash_id,
            certificate_json=cert.certificate_json,
            certificate_pdf_path=cert.certificate_pdf_path,
            sources_used=cert.sources_used,
            rules_applied=cert.rules_applied,
            jurisdiction_id=cert.jurisdiction_id,
            confidence_score=cert.confidence_score,
            ai_explanation=cert.ai_explanation,
            issued_at=cert.issued_at,
            issued_by_user_id=cert.issued_by_user_id,
        )
        for cert in certificates
    ]


# ========== Blockchain Anchoring Endpoints ==========

@router.post("/anchor", response_model=list[BlockchainAnchorResponse])
def anchor_hashes(
    payload: AnchorHashRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
) -> list[BlockchainAnchorResponse]:
    """Anchor entity hash(es) to blockchain.
    
    RBAC: ADMIN only (blockchain transactions are critical)
    """
    
    try:
        if payload.batch_mode and len(payload.hash_ids) > 1:
            anchors = anchor_batch_hashes(
                db,
                hash_ids=payload.hash_ids,
                user_id=current_user.id,
                blockchain_network=payload.blockchain_network,
            )
        elif len(payload.hash_ids) == 1:
            anchor = anchor_single_hash(
                db,
                hash_id=payload.hash_ids[0],
                user_id=current_user.id,
                blockchain_network=payload.blockchain_network,
            )
            anchors = [anchor]
        else:
            raise HTTPException(status_code=400, detail="Must provide at least one hash_id")
    except ValueError as exc:
        msg = str(exc)
        lowered = msg.lower()
        if "not configured" in lowered or "connect" in lowered:
            raise HTTPException(status_code=503, detail=msg) from exc
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    
    # Record audit event
    for anchor in anchors:
        record_audit_event(
            db,
            event=AuditEvent(
                actor_user_id=current_user.id,
                action="BLOCKCHAIN_ANCHORED",
                entity_type="entity_hash",
                entity_id=str(anchor.hash_id) if anchor.hash_id else None,
                metadata={
                    "anchor_id": anchor.id,
                    "transaction_hash": anchor.transaction_hash,
                },
            ),
            commit=True,
        )
    
    return [
        BlockchainAnchorResponse(
            id=anchor.id,
            hash_id=anchor.hash_id,
            merkle_root=anchor.merkle_root,
            batch_id=anchor.batch_id,
            blockchain_network=anchor.blockchain_network,
            transaction_hash=anchor.transaction_hash,
            block_number=anchor.block_number,
            block_timestamp=anchor.block_timestamp,
            anchor_type=anchor.anchor_type,
            anchored_at=anchor.anchored_at,
            explorer_url=anchor.explorer_url,
        )
        for anchor in anchors
    ]


@router.get("/anchor/verify/{anchor_id}", response_model=VerifyAnchorResponse)
def verify_blockchain_anchor(
    anchor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> VerifyAnchorResponse:
    """Verify blockchain anchor (check transaction on-chain).
    
    RBAC: All authenticated users
    """
    
    try:
        result = verify_anchor(db, anchor_id)
    except ValueError as exc:
        msg = str(exc)
        lowered = msg.lower()
        if "not configured" in lowered or "connect" in lowered:
            raise HTTPException(status_code=503, detail=msg) from exc
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    
    return VerifyAnchorResponse(
        anchor_id=result["anchor_id"],
        transaction_hash=result["transaction_hash"],
        blockchain_network=result["blockchain_network"],
        explorer_url=result.get("explorer_url"),
        verified=result["verified"],
        confirmation_status=result["confirmation_status"],
        note=result.get("note"),
    )


# ========== Full Verification Endpoint ==========

@router.get("/verify/{entity_type}/{entity_id}", response_model=FullVerificationResponse)
def get_full_verification(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> FullVerificationResponse:
    """Get complete verification information for an entity.
    
    Includes: current hash, latest certificate, blockchain anchor, audit trail.
    
    RBAC: All authenticated users
    """
    
    # Get latest hash
    entity_hash = get_latest_hash(db, entity_type, entity_id)
    if not entity_hash:
        raise HTTPException(status_code=404, detail="Entity not found or never hashed")
    
    # Get latest certificate
    certificates = get_certificates_for_entity(db, entity_type, entity_id)
    latest_cert = certificates[0] if certificates else None
    
    # Get blockchain anchor
    blockchain_anchor = None
    if entity_hash:
        anchor = get_anchor_for_hash(db, entity_hash.id)
        if anchor:
            blockchain_anchor = BlockchainAnchorResponse(
                id=anchor.id,
                hash_id=anchor.hash_id,
                merkle_root=anchor.merkle_root,
                batch_id=anchor.batch_id,
                blockchain_network=anchor.blockchain_network,
                transaction_hash=anchor.transaction_hash,
                block_number=anchor.block_number,
                block_timestamp=anchor.block_timestamp,
                anchor_type=anchor.anchor_type,
                anchored_at=anchor.anchored_at,
                explorer_url=anchor.explorer_url,
            )
    
    # Get audit trail
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == str(entity_id))
        .order_by(AuditLog.occurred_at.desc())
        .limit(50)
        .all()
    )
    
    audit_trail = [
        {
            "id": log.id,
            "event": log.action,
            "user_id": log.actor_user_id,
            "timestamp": log.occurred_at.isoformat(),
            "metadata": log.metadata_,
            "hash_before": log.hash_before if hasattr(log, "hash_before") else None,
            "hash_after": log.hash_after if hasattr(log, "hash_after") else None,
        }
        for log in audit_logs
    ]
    
    # Get entity name
    from app.trust.certificates import _get_entity_name
    entity_name = _get_entity_name(db, entity_type, entity_id)
    
    return FullVerificationResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_hash=EntityHashResponse(
            id=entity_hash.id,
            entity_type=entity_hash.entity_type,
            entity_id=entity_hash.entity_id,
            hash_algorithm=entity_hash.hash_algorithm,
            hash_value=entity_hash.hash_value,
            timestamp=entity_hash.timestamp,
            computed_by_user_id=entity_hash.computed_by_user_id,
        ),
        certificate=CertificateResponse(
            id=latest_cert.id,
            entity_type=latest_cert.entity_type,
            entity_id=latest_cert.entity_id,
            certificate_type=latest_cert.certificate_type,
            verification_status=latest_cert.verification_status,
            hash_id=latest_cert.hash_id,
            certificate_json=latest_cert.certificate_json,
            certificate_pdf_path=latest_cert.certificate_pdf_path,
            sources_used=latest_cert.sources_used,
            rules_applied=latest_cert.rules_applied,
            jurisdiction_id=latest_cert.jurisdiction_id,
            confidence_score=latest_cert.confidence_score,
            ai_explanation=latest_cert.ai_explanation,
            issued_at=latest_cert.issued_at,
            issued_by_user_id=latest_cert.issued_by_user_id,
        ) if latest_cert else None,
        blockchain_anchor=blockchain_anchor,
        audit_trail=audit_trail,
    )
