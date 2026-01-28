"""Heraldry Service — Orchestration of heraldic validation with audit and AI.

Integrates:
- Blazon parsing
- Rule validation
- Jurisdiction compliance
- SVG generation
- AI explainability
- Audit logging
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import get_openai_client
from app.ai.schemas import SourceReference
from app.core.audit import AuditEvent, record_audit_event
from app.heraldry.blazon_parser import parse_blazon
from app.heraldry.jurisdiction_compliance import validate_jurisdiction_compliance
from app.heraldry.rule_validator import validate_heraldry
from app.heraldry.schemas import (
    HeraldryExplanation,
    HeraldryFullValidationRequest,
    FullValidationResponse,
    ParsedBlazonResponse,
    ValidationResultResponse,
    RuleViolationResponse,
    JurisdictionComplianceResponse,
)
from app.heraldry.svg_generator import generate_svg
from app.heraldic_entities.models import HeraldicEntity
from app.jurisdictions.models import Jurisdiction
from app.persons.models import Person
from app.sources.models import Source


def _source_refs(db: Session, *, source_ids: list[int]) -> list[SourceReference]:
    if not source_ids:
        return []

    ids = sorted({int(sid) for sid in source_ids})
    sources = db.scalars(select(Source).where(Source.id.in_(ids))).all()
    sources.sort(key=lambda s: s.id)

    def _issued(d: date | None) -> str | None:
        return d.isoformat() if d else None

    return [
        SourceReference(
            id=s.id,
            source_type=s.source_type,
            citation=s.citation,
            url=s.url,
            issued_date=_issued(s.issued_date),
        )
        for s in sources
    ]


def _sources_for_heraldry(
    db: Session,
    *,
    jurisdiction_id: int | None,
    claimant_person_id: int | None,
) -> list[SourceReference]:
    source_ids: set[int] = set()

    if jurisdiction_id is not None:
        juris = db.get(Jurisdiction, jurisdiction_id)
        if juris is not None:
            source_ids.update(juris.source_ids)

    if claimant_person_id is not None:
        claimant = db.get(Person, claimant_person_id)
        if claimant is not None:
            source_ids.update(claimant.source_ids)

    return _source_refs(db, source_ids=sorted(source_ids))


def _generate_ai_explanation(
    *,
    blazon: str,
    parsed_valid: bool,
    rule_violations: list[dict],
    jurisdiction_violations: list[str],
    overall_valid: bool,
    confidence: float,
    sources: list[SourceReference],
    rules_applied: dict[str, Any],
) -> HeraldryExplanation:
    """Generate AI explanation for heraldic validation.

    Narrative fields may be AI-generated, but meta fields (confidence/sources/rules_applied)
    are deterministic and never taken from the model.
    """
    client = get_openai_client()
    if not client:
        return HeraldryExplanation(
            summary="AI explanation unavailable (no OpenAI key)",
            detailed_reasoning="OpenAI API key not configured. Validation completed using deterministic rules.",
            citations=[{"category": "system", "description": "No AI explanation available"}],
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
        )
    
    # Build prompt citing database-stored rules
    prompt = f"""Analyze the following heraldic blazon validation result and provide a historically-grounded explanation.

Blazon: "{blazon}"

Parsing Result: {"Valid" if parsed_valid else "Invalid"}

Rule Violations:
{chr(10).join([f"- {v['rule_name']}: {v['message']} (severity: {v['severity']})" for v in rule_violations]) if rule_violations else "None"}

Jurisdiction Violations:
{chr(10).join([f"- {v}" for v in jurisdiction_violations]) if jurisdiction_violations else "None"}

Overall Valid: {overall_valid}

Provide:
1. A one-sentence summary of the validation result
2. Detailed historical reasoning citing only the specific rules violated or passed
3. Citations to the heraldic rules used (Rule of Tincture, jurisdictional law, temporal legitimacy, etc.)

DO NOT invent historical facts. Only reference the rules explicitly stated above."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a heraldic expert analyzing coat of arms validity based solely on provided rule violations. Cite only the rules given. No speculation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse response (simplified)
        lines = content.strip().split('\n')
        summary = lines[0] if lines else "Validation complete."
        detailed = content
        
        # Build citations from violated rules
        citations = []
        if rule_violations:
            for v in rule_violations:
                citations.append({
                    "category": "heraldic_rule",
                    "description": f"{v['rule_name']}: {v['message']}",
                })
        if jurisdiction_violations:
            for jv in jurisdiction_violations:
                citations.append({
                    "category": "jurisdictional_law",
                    "description": jv,
                })
        if not citations:
            citations.append({"category": "validation", "description": "No violations detected; arms conform to heraldic rules"})
        
        return HeraldryExplanation(
            summary=summary[:200],
            detailed_reasoning=detailed,
            citations=citations,
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
        )
    except Exception as e:
        return HeraldryExplanation(
            summary=f"AI explanation failed: {str(e)[:100]}",
            detailed_reasoning="Error generating AI explanation. Validation results are still valid.",
            citations=[{"category": "error", "description": str(e)[:200]}],
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
        )


def full_heraldic_validation(
    db: Session,
    *,
    payload: HeraldryFullValidationRequest,
    actor_user_id: int,
) -> tuple[FullValidationResponse, int]:
    """Perform full heraldic validation with all engines.
    
    Steps:
    1. Parse blazon
    2. Validate heraldic rules
    3. Check jurisdiction compliance
    4. Generate SVG (only if valid)
    5. Generate AI explanation
    6. Record audit log
    7. Update or create HeraldicEntity record
    
    Returns:
        (FullValidationResponse, audit_id)
    """
    # Step 1: Parse blazon
    parsed = parse_blazon(payload.blazon)
    
    # Step 2: Validate heraldic rules
    rule_validation = validate_heraldry(
        parsed,
        as_of=payload.as_of,
        strict_mode=payload.strict_mode,
    )
    
    # Step 3: Jurisdiction compliance (if jurisdiction provided)
    jurisdiction_compliance = None
    if payload.jurisdiction_id:
        jurisdiction_compliance = validate_jurisdiction_compliance(
            db,
            parsed_blazon=parsed,
            jurisdiction_id=payload.jurisdiction_id,
            claimant_person_id=payload.claimant_person_id,
            as_of=payload.as_of,
        )
    
    # Determine overall validity
    overall_valid = (
        parsed.valid
        and rule_validation.valid
        and (jurisdiction_compliance is None or jurisdiction_compliance.compliant)
    )
    
    # Step 4: Generate SVG (only if valid and requested)
    svg = None
    if payload.generate_svg and overall_valid:
        svg = generate_svg(parsed, valid=True)
    
    # Step 5: Generate AI explanation
    rule_violations_dict = [v.to_dict() for v in rule_validation.violations + rule_validation.warnings]
    jurisdiction_violations_list = jurisdiction_compliance.violations if jurisdiction_compliance else []

    confidence = 1.0 if overall_valid else 0.0
    sources = _sources_for_heraldry(
        db,
        jurisdiction_id=payload.jurisdiction_id,
        claimant_person_id=payload.claimant_person_id,
    )
    rules_applied: dict[str, Any] = {
        "as_of": payload.as_of.isoformat() if payload.as_of else None,
        "strict_mode": payload.strict_mode,
        "parsed_valid": parsed.valid,
        "field_tincture": parsed.field_tincture,
        "field_tincture_type": parsed.field_tincture_type.value,
        "rule_validation": {
            "valid": rule_validation.valid,
            "pass_rules": rule_validation.pass_rules,
            "violations": [v.to_dict() for v in rule_validation.violations],
            "warnings": [w.to_dict() for w in rule_validation.warnings],
        },
        "jurisdiction_compliance": jurisdiction_compliance.to_dict() if jurisdiction_compliance else None,
        "overall_valid": overall_valid,
    }

    explanation = _generate_ai_explanation(
        blazon=payload.blazon,
        parsed_valid=parsed.valid,
        rule_violations=rule_violations_dict,
        jurisdiction_violations=jurisdiction_violations_list,
        overall_valid=overall_valid,
        confidence=confidence,
        sources=sources,
        rules_applied=rules_applied,
    )
    
    # Build response
    response = FullValidationResponse(
        parsed_blazon=ParsedBlazonResponse(
            field_tincture=parsed.field_tincture,
            field_tincture_type=parsed.field_tincture_type.value,
            charges=parsed.charges,
            ordinaries=parsed.ordinaries,
            partitions=parsed.partitions,
            valid=parsed.valid,
            errors=parsed.errors,
            raw_blazon=parsed.raw_blazon,
        ),
        rule_validation=ValidationResultResponse(
            valid=rule_validation.valid,
            violations=[RuleViolationResponse(**v.to_dict()) for v in rule_validation.violations],
            warnings=[RuleViolationResponse(**w.to_dict()) for w in rule_validation.warnings],
            pass_rules=rule_validation.pass_rules,
        ),
        jurisdiction_compliance=JurisdictionComplianceResponse(**jurisdiction_compliance.to_dict()) if jurisdiction_compliance else None,
        svg=svg,
        overall_valid=overall_valid,
        explanation=explanation,
        audit_id=0,  # Will be filled after audit
    )
    
    # Step 6: Record audit event
    audit = record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor_user_id,
            action="VALIDATE.HERALDRY",
            entity_type="heraldic_entity",
            entity_id="new",
            metadata={"result": response.model_dump(mode="json")},
        ),
        commit=True,
    )
    
    response.audit_id = audit.id
    
    # Step 7: Create or update HeraldicEntity record
    entity = HeraldicEntity(
        name=f"Blazon: {payload.blazon[:50]}...",
        jurisdiction_id=payload.jurisdiction_id,
        blazon=payload.blazon,
        parsed_structure=parsed.to_dict(),
        validation_status="VALID" if overall_valid else "INVALID",
        validation_errors={"errors": parsed.errors} if parsed.errors else None,
        svg_cache=svg,
        rule_violations={"violations": rule_violations_dict},
        jurisdiction_compliant=jurisdiction_compliance.compliant if jurisdiction_compliance else None,
        jurisdiction_compliance_detail=jurisdiction_compliance.detail if jurisdiction_compliance else None,
        last_validation_check=datetime.now(timezone.utc),
        claimant_person_id=payload.claimant_person_id,
        valid_from=payload.as_of or datetime.now(timezone.utc).date(),
        notes=f"Validated via Day 8 engine. Overall valid: {overall_valid}",
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    
    # Update audit entity_id with actual entity ID
    audit.entity_id = str(entity.id)
    db.commit()
    
    return response, audit.id
