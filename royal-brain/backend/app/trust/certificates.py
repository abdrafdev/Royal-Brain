"""Verification Certificate Generator — Day 9.

Generates machine-readable (JSON) and optional human-readable (PDF) certificates.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy.orm import Session

from app.ai.client import get_openai_client
from app.trust.hashing import (
    get_latest_hash,
    hash_family,
    hash_heraldic_entity,
    hash_order,
    hash_person,
    hash_title,
)
from app.trust.models import VerificationCertificate


class VerificationStatus(str, Enum):
    """Verification status for certificates."""
    VALID = "VALID"
    INVALID = "INVALID"
    UNCERTAIN = "UNCERTAIN"
    PENDING = "PENDING"


def _generate_ai_certificate_explanation(
    *,
    entity_type: str,
    entity_data: dict,
    sources_used: list[dict],
    rules_applied: list[dict],
    verification_status: str,
) -> str:
    """Generate AI explanation for certificate."""
    client = get_openai_client()
    if not client:
        return f"Entity verified as {verification_status}. AI explanation unavailable (no OpenAI API key configured)."
    
    prompt = f"""Generate a concise certificate explanation for this verified entity.

Entity Type: {entity_type}
Entity Data: {entity_data}
Verification Status: {verification_status}

Sources Used:
{chr(10).join([f"- {s.get('name', 'Unknown')} ({s.get('type', 'unknown')})" for s in sources_used]) if sources_used else "None"}

Rules Applied:
{chr(10).join([f"- {r.get('rule_name', 'Unknown')}: {r.get('result', 'unknown')}" for r in rules_applied]) if rules_applied else "None"}

Provide:
1. A brief summary of the verification
2. Key evidence from sources
3. Confidence assessment

Keep response under 300 words. Cite only the sources and rules listed above."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a verification specialist. Explain certificate validity concisely, citing only provided sources and rules."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content or "Verification complete."
    except Exception as e:
        return f"Entity verified as {verification_status}. AI explanation generation failed: {str(e)[:100]}"


def generate_certificate(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    certificate_type: str,
    user_id: int,
    jurisdiction_id: int | None = None,
    sources_used: list[dict] | None = None,
    rules_applied: list[dict] | None = None,
    verification_status: VerificationStatus = VerificationStatus.VALID,
    confidence_score: float | None = None,
) -> VerificationCertificate:
    """Generate verification certificate for an entity."""
    
    # Get or compute current hash
    entity_hash = get_latest_hash(db, entity_type, entity_id)
    if not entity_hash:
        # Compute new hash
        if entity_type == "Person":
            entity_hash = hash_person(db, entity_id, user_id=user_id)
        elif entity_type == "Title":
            entity_hash = hash_title(db, entity_id, user_id=user_id)
        elif entity_type == "HeraldicEntity":
            entity_hash = hash_heraldic_entity(db, entity_id, user_id=user_id)
        elif entity_type == "Order":
            entity_hash = hash_order(db, entity_id, user_id=user_id)
        elif entity_type == "Family":
            entity_hash = hash_family(db, entity_id, user_id=user_id)
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")
    
    # Fetch entity name
    entity_name = _get_entity_name(db, entity_type, entity_id)
    
    # Build certificate JSON
    certificate_json = {
        "certificate_id": None,  # Will be set after DB insert
        "certificate_type": certificate_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "verification_status": verification_status.value,
        "hash": {
            "algorithm": entity_hash.hash_algorithm,
            "value": entity_hash.hash_value,
            "timestamp": entity_hash.timestamp.isoformat(),
        },
        "jurisdiction_id": jurisdiction_id,
        "sources_used": sources_used or [],
        "rules_applied": rules_applied or [],
        "confidence_score": confidence_score,
        "issued_at": datetime.now().isoformat(),
        "issued_by_user_id": user_id,
    }
    
    # Generate AI explanation
    ai_explanation = _generate_ai_certificate_explanation(
        entity_type=entity_type,
        entity_data={"name": entity_name, "id": entity_id},
        sources_used=sources_used or [],
        rules_applied=rules_applied or [],
        verification_status=verification_status.value,
    )
    
    # Create certificate record
    certificate = VerificationCertificate(
        entity_type=entity_type,
        entity_id=entity_id,
        certificate_type=certificate_type,
        verification_status=verification_status.value,
        hash_id=entity_hash.id,
        certificate_json=certificate_json,
        certificate_pdf_path=None,  # PDF generation optional
        sources_used={"sources": sources_used or []},
        rules_applied={"rules": rules_applied or []},
        jurisdiction_id=jurisdiction_id,
        confidence_score=confidence_score,
        ai_explanation=ai_explanation,
        issued_by_user_id=user_id,
    )
    
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    
    # Update certificate JSON with ID.
    # NOTE: SQLAlchemy JSON columns do not always detect in-place dict mutations;
    # re-assign to ensure persistence.
    updated_json = dict(certificate.certificate_json)
    updated_json["certificate_id"] = certificate.id
    certificate.certificate_json = updated_json
    db.commit()

    return certificate


def _get_entity_name(db: Session, entity_type: str, entity_id: int) -> str:
    """Get entity display name."""
    if entity_type == "Person":
        from app.persons.models import Person
        person = db.get(Person, entity_id)
        return person.primary_name if person else f"Person {entity_id}"
    elif entity_type == "Title":
        from app.titles.models import Title
        title = db.get(Title, entity_id)
        return title.name if title else f"Title {entity_id}"
    elif entity_type == "HeraldicEntity":
        from app.heraldic_entities.models import HeraldicEntity
        entity = db.get(HeraldicEntity, entity_id)
        return entity.name if entity else f"HeraldicEntity {entity_id}"
    elif entity_type == "Order":
        from app.orders.models import Order
        order = db.get(Order, entity_id)
        return order.name if order else f"Order {entity_id}"
    elif entity_type == "Family":
        from app.families.models import Family
        family = db.get(Family, entity_id)
        return family.name if family else f"Family {entity_id}"
    else:
        return f"{entity_type} {entity_id}"


def get_certificate(db: Session, certificate_id: int) -> VerificationCertificate | None:
    """Retrieve certificate by ID."""
    return db.get(VerificationCertificate, certificate_id)


def get_certificates_for_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> list[VerificationCertificate]:
    """Get all certificates for an entity."""
    return (
        db.query(VerificationCertificate)
        .filter(
            VerificationCertificate.entity_type == entity_type,
            VerificationCertificate.entity_id == entity_id,
        )
        .order_by(VerificationCertificate.issued_at.desc())
        .all()
    )
