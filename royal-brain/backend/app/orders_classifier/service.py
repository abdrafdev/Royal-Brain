from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.genealogy.service import check_timeline_consistency
from app.jurisdictions.models import Jurisdiction
from app.orders.models import Order
from app.persons.models import Person
from app.sources.models import Source
from app.succession.schemas import SuccessionEvaluationRequest
from app.succession.service import evaluate_succession
from app.validation.jurisdiction_service import compare_jurisdictions
from app.validation.schemas import (
    OrderValidationFactors,
    OrderValidationRequest,
    OrderValidationResult,
)


def _check_fons_honorum(order: Order, db: Session) -> tuple[bool, str]:
    """Check if fons honorum (source of authority) is valid."""
    if order.fons_honorum_person_id is None:
        return False, "No fons honorum person recorded; cannot verify authority source."
    
    fons = db.get(Person, order.fons_honorum_person_id)
    if fons is None:
        return False, f"Fons honorum person #{order.fons_honorum_person_id} not found in database."
    
    return True, f"Fons honorum: {fons.primary_name} (person #{fons.id})."


def _check_succession(
    order: Order,
    claimant_person_id: int,
    as_of: date | None,
    db: Session,
) -> tuple[bool | None, str]:
    """Run Day 4 succession engine if fons honorum exists."""
    if order.fons_honorum_person_id is None:
        return None, "No fons honorum recorded; succession check not applicable."
    
    # Get jurisdiction succession rules if order has a jurisdiction
    rule_type = "agnatic"  # default
    if order.jurisdiction_id:
        juris = db.get(Jurisdiction, order.jurisdiction_id)
        if juris and juris.succession_rules_json:
            rule_type = juris.succession_rules_json.get("succession_rule_type", "agnatic")
    
    payload = SuccessionEvaluationRequest(
        root_person_id=order.fons_honorum_person_id,
        candidate_person_id=claimant_person_id,
        rule_type=rule_type,
        as_of=as_of,
    )
    
    try:
        result = evaluate_succession(db, payload)
        if result.status == "VALID":
            return True, f"Succession VALID: claimant has legitimate line from fons honorum (rule: {rule_type})."
        elif result.status == "INVALID":
            reason_summary = "; ".join([r.message for r in result.reasons[:2]])  # first 2 reasons
            return False, f"Succession INVALID: {reason_summary}"
        else:  # UNCERTAIN
            reason_summary = "; ".join([r.message for r in result.reasons[:2]])
            return None, f"Succession UNCERTAIN: {reason_summary}"
    except ValueError as exc:
        return None, f"Succession check failed: {exc}"


def _check_jurisdiction_recognition(order: Order, db: Session) -> dict[str, list[str]]:
    """Check which jurisdictions recognize this order (Day 6 integration)."""
    if not order.recognized_by:
        return {"recognized": [], "not_recognized": [], "partial": []}
    
    # Use Day 6 compare_jurisdictions helper
    return compare_jurisdictions(
        db,
        jurisdiction_codes=order.recognized_by,
        order_name=order.name,
    )


def _check_documentation(order: Order, db: Session) -> tuple[int, str]:
    """Score documentary evidence (0-100)."""
    score = 0
    details: list[str] = []
    
    # Source documents linked
    if order.source_ids:
        score += 30
        details.append(f"{len(order.source_ids)} source(s) linked.")
    else:
        details.append("No sources linked.")
    
    # Founding document exists
    if order.founding_document_source_id:
        founding_doc = db.get(Source, order.founding_document_source_id)
        if founding_doc:
            score += 40
            details.append(f"Founding document: {founding_doc.citation}")
        else:
            details.append("Founding document ID invalid.")
    else:
        details.append("No founding document recorded.")
    
    # Granted date recorded
    if order.granted_date:
        score += 15
        details.append(f"Granted date: {order.granted_date}")
    else:
        details.append("No granted date recorded.")
    
    # Grantor recorded
    if order.grantor_person_id:
        score += 15
        details.append(f"Grantor: person #{order.grantor_person_id}")
    else:
        details.append("No grantor recorded.")
    
    return score, " ".join(details)


def _check_timeline(claimant_person_id: int, as_of: date | None, db: Session) -> tuple[int, str]:
    """Run Day 3 timeline checks on claimant subgraph."""
    try:
        genealogy = check_timeline_consistency(db, root_person_id=claimant_person_id, depth=3, as_of=as_of)
        error_count = len([i for i in genealogy.issues if i.severity == "error"])
        warning_count = len([i for i in genealogy.issues if i.severity == "warning"])
        
        if error_count == 0 and warning_count == 0:
            return 0, "No timeline issues detected."
        else:
            return error_count + warning_count, f"{error_count} error(s), {warning_count} warning(s)."
    except ValueError:
        return 0, "Timeline check not applicable (person not found)."


def _calculate_legitimacy_score(factors: OrderValidationFactors) -> int:
    """Calculate overall legitimacy score (0-100) from validation factors."""
    score = 0
    
    # Fons honorum validity: 25 points
    if factors.fons_honorum_valid:
        score += 25
    
    # Succession validity: 35 points
    if factors.succession_valid is True:
        score += 35
    elif factors.succession_valid is None:
        score += 10  # partial credit if not evaluated
    # else: 0 points if invalid
    
    # Jurisdiction recognition: 15 points
    recognized_count = len(factors.jurisdiction_recognition.get("recognized", []))
    if recognized_count > 0:
        score += min(15, recognized_count * 5)
    
    # Documentation: 15 points (scaled from 0-100 doc score)
    score += int(factors.documentation_score * 0.15)
    
    # Timeline issues penalty: -10 points (capped)
    penalty = min(10, factors.timeline_issues_count * 2)
    score -= penalty
    
    return max(0, min(100, score))


def _classify_order(legitimacy_score: int, fraud_flags: list[str]) -> str:
    """Classify order based on score and fraud flags."""
    if fraud_flags:
        if legitimacy_score < 30:
            return "FRAUDULENT"
        else:
            return "DISPUTED"
    
    if legitimacy_score >= 70:
        return "LEGITIMATE"
    elif legitimacy_score >= 40:
        return "DISPUTED"
    else:
        return "SELF_STYLED"


def _detect_fraud_flags(order: Order, factors: OrderValidationFactors) -> list[str]:
    """Detect potential fraud indicators based on stored data (no hallucination)."""
    flags: list[str] = []
    
    # Missing foundational data
    if not factors.fons_honorum_valid:
        flags.append("MISSING_FONS_HONORUM")
    
    if factors.succession_valid is False:
        flags.append("INVALID_SUCCESSION")
    
    if factors.documentation_score < 30:
        flags.append("INSUFFICIENT_DOCUMENTATION")
    
    if factors.timeline_issues_count > 3:
        flags.append("TIMELINE_INCONSISTENCIES")
    
    # No jurisdiction recognition
    if not factors.jurisdiction_recognition.get("recognized"):
        flags.append("NO_JURISDICTION_RECOGNITION")
    
    # Order name patterns (basic check; not exhaustive)
    if order.name and ("self-styled" in order.name.lower() or "sovereign" in order.name.lower()):
        flags.append("SUSPICIOUS_NAME_PATTERN")
    
    return flags


def validate_order(
    db: Session,
    *,
    payload: OrderValidationRequest,
    actor_user_id: int,
) -> tuple[OrderValidationResult, int]:
    """Validate a chivalric order's legitimacy using Day 3/4/6 engines."""
    order = db.get(Order, payload.order_id)
    if order is None:
        raise ValueError("Order not found")
    
    claimant = db.get(Person, payload.claimant_person_id)
    if claimant is None:
        raise ValueError("Claimant person not found")
    
    # Run validation checks
    fons_valid, fons_detail = _check_fons_honorum(order, db)
    succession_valid, succession_detail = _check_succession(
        order, payload.claimant_person_id, payload.as_of, db
    )
    jurisdiction_recognition = _check_jurisdiction_recognition(order, db)
    documentation_score, documentation_detail = _check_documentation(order, db)
    timeline_issues_count, timeline_detail = _check_timeline(
        payload.claimant_person_id, payload.as_of, db
    )
    
    factors = OrderValidationFactors(
        fons_honorum_valid=fons_valid,
        fons_honorum_detail=fons_detail,
        succession_valid=succession_valid,
        succession_detail=succession_detail,
        jurisdiction_recognition=jurisdiction_recognition,
        documentation_score=documentation_score,
        documentation_detail=documentation_detail,
        timeline_issues_count=timeline_issues_count,
        timeline_detail=timeline_detail,
    )
    
    # Calculate score and detect fraud
    legitimacy_score = _calculate_legitimacy_score(factors)
    fraud_flags = _detect_fraud_flags(order, factors)
    classification = _classify_order(legitimacy_score, fraud_flags)
    
    # Collect sources
    sources: set[int] = set(order.source_ids)
    if order.founding_document_source_id:
        sources.add(order.founding_document_source_id)
    if order.jurisdiction_id:
        juris = db.get(Jurisdiction, order.jurisdiction_id)
        if juris:
            sources.update(juris.source_ids)
    
    result = OrderValidationResult(
        order_id=order.id,
        order_name=order.name,
        claimant_person_id=payload.claimant_person_id,
        classification=classification,
        legitimacy_score=legitimacy_score,
        fraud_flags=fraud_flags,
        factors=factors,
        sources=sorted(list(sources)),
    )
    
    # Update order row with validation results
    order.classification = classification
    order.legitimacy_score = legitimacy_score
    order.fraud_flags = fraud_flags
    order.last_legitimacy_check = datetime.now(timezone.utc)
    db.flush()
    
    # Record audit event
    audit = record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor_user_id,
            action="VALIDATE.ORDER",
            entity_type="order",
            entity_id=str(order.id),
            metadata={"result": result.model_dump(mode="json")},
        ),
        commit=True,
    )
    
    return result, audit.id
