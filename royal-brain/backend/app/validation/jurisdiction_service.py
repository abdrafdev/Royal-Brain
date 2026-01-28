from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.genealogy.service import check_timeline_consistency
from app.jurisdictions.models import Jurisdiction
from app.succession.schemas import CustomRule, SuccessionEvaluationRequest, SuccessionEvaluationResult
from app.succession.service import evaluate_succession
from app.titles.models import Title
from app.validation.schemas import (
    JurisdictionContext,
    JurisdictionRuleCheck,
    JurisdictionTitleValidationResult,
    TimeValidityResult,
)


def _parse_date_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def check_time_validity(
    *,
    granted_date: date | None,
    abolished_date: date | None,
    rules_json: dict | None,
) -> TimeValidityResult:
    """Check whether a grant falls into a legally active / historic / invalid window."""
    if abolished_date is None:
        return TimeValidityResult(
            valid=True,
            status="active",
            reason="No abolition date is recorded for this jurisdiction.",
        )

    restored_date = None
    if rules_json and isinstance(rules_json, dict):
        restored_date = _parse_date_iso(rules_json.get("nobility_restored_date"))

    if granted_date is None:
        return TimeValidityResult(
            valid=False,
            status="uncertain",
            reason="Title grant date is not recorded; cannot evaluate time-based validity.",
        )

    # If there is a restoration date, handle the abolished interval explicitly.
    if restored_date is not None:
        if granted_date < abolished_date:
            return TimeValidityResult(
                valid=True,
                status="historic_recognition_only",
                reason="Grant predates abolition; treated as historic recognition.",
            )
        if abolished_date <= granted_date < restored_date:
            return TimeValidityResult(
                valid=False,
                status="invalid",
                reason="Grant falls within an abolished period for this jurisdiction.",
            )
        return TimeValidityResult(
            valid=True,
            status="active",
            reason="Grant postdates restoration; treated as active recognition.",
        )

    if granted_date < abolished_date:
        return TimeValidityResult(
            valid=True,
            status="historic_recognition_only",
            reason="Grant predates abolition; treated as historic recognition.",
        )

    return TimeValidityResult(
        valid=False,
        status="invalid",
        reason="Grant postdates abolition; treated as invalid under jurisdiction rules.",
    )


def check_jurisdiction_rules(*, title_rank: str | None, jurisdiction: Jurisdiction) -> JurisdictionRuleCheck:
    """Lightweight, non-hallucinatory rule checks for a title type/rank.

    This returns conditions/requirements derived only from stored jurisdiction fields.
    """

    conditions: list[str] = []
    requirements: list[str] = []

    # If we have explicit legal references, list them as requirements.
    if jurisdiction.legal_references:
        requirements.extend(jurisdiction.legal_references)

    # If the jurisdiction has a general note, surface it as a condition.
    if jurisdiction.succession_rules_json and isinstance(jurisdiction.succession_rules_json, dict):
        note = jurisdiction.succession_rules_json.get("note")
        if isinstance(note, str) and note.strip():
            conditions.append(note.strip())

        authority = jurisdiction.succession_rules_json.get("authority")
        if isinstance(authority, list) and authority:
            conditions.append("Authority: " + ", ".join([str(a) for a in authority if a]))

    # Rank-based heuristic (no external assumptions)
    if title_rank:
        conditions.append(f"Title rank recorded as '{title_rank}'.")

    return JurisdictionRuleCheck(allowed=True, conditions=conditions, requirements=requirements)


def compare_jurisdictions(
    db: Session,
    *,
    jurisdiction_codes: list[str],
    order_name: str | None = None,
) -> dict[str, list[str]]:
    """Compare recognition across multiple jurisdictions.

    If order_name is provided, uses jurisdictions.recognized_orders to classify.
    Otherwise returns presence/absence of the jurisdiction record.

    Returns:
      {"recognized": [...], "not_recognized": [...], "partial": [...]}.
    """

    codes = [c.strip().upper() for c in jurisdiction_codes if c and c.strip()]
    rows = db.query(Jurisdiction).filter(Jurisdiction.code.in_(codes)).all()
    by_code = {j.code: j for j in rows if j.code}

    recognized: list[str] = []
    not_recognized: list[str] = []
    partial: list[str] = []

    for code in codes:
        j = by_code.get(code)
        if j is None:
            not_recognized.append(code)
            continue

        if order_name is None:
            recognized.append(code)
            continue

        ro = j.recognized_orders or []
        if not ro:
            partial.append(code)
            continue

        needle = order_name.lower().strip()
        match = any(needle in str(x).lower() for x in ro)
        if match:
            # If nobility is abolished, treat as partial/historic recognition.
            if j.nobility_abolished_date is not None:
                partial.append(code)
            else:
                recognized.append(code)
        else:
            not_recognized.append(code)

    return {"recognized": recognized, "not_recognized": not_recognized, "partial": partial}


def _succession_payload_from_jurisdiction(jurisdiction: Jurisdiction, *, root_id: int, candidate_id: int, as_of: date | None) -> SuccessionEvaluationRequest:
    rules = jurisdiction.succession_rules_json if isinstance(jurisdiction.succession_rules_json, dict) else {}

    rule_type = rules.get("succession_rule_type")
    if rule_type not in {"agnatic", "cognatic", "salic", "semi_salic", "custom"}:
        # Default to agnatic if not specified; this is deterministic and will be disclosed by AI.
        rule_type = "agnatic"

    custom_rule = None
    if rule_type == "custom":
        custom_rule = CustomRule(
            allow_female_inheritance=bool(rules.get("allow_female_inheritance", False)),
            allow_female_transmission=bool(rules.get("allow_female_transmission", True)),
            allow_adoption=bool(rules.get("allow_adoption", False)),
            max_depth=rules.get("max_depth", 12),
        )

    return SuccessionEvaluationRequest(
        root_person_id=root_id,
        candidate_person_id=candidate_id,
        rule_type=rule_type,
        as_of=as_of,
        custom_rule=custom_rule,
    )


def validate_title_claim(
    db: Session,
    *,
    person_id: int,
    title_id: int,
    actor_user_id: int,
    as_of: date | None,
) -> tuple[JurisdictionTitleValidationResult, int]:
    title = db.get(Title, title_id)
    if title is None:
        raise ValueError("Title not found")

    jurisdiction = db.get(Jurisdiction, title.jurisdiction_id) if title.jurisdiction_id else None

    # Genealogy/timeline checks for the claimant subgraph.
    genealogy = check_timeline_consistency(db, root_person_id=person_id, depth=4, as_of=as_of)

    # Time validity is computed from granted_date (preferred) falling back to valid_from.
    granted_date = title.granted_date or title.valid_from
    time_validity = (
        check_time_validity(
            granted_date=granted_date,
            abolished_date=jurisdiction.nobility_abolished_date if jurisdiction else None,
            rules_json=jurisdiction.succession_rules_json if jurisdiction else None,
        )
        if jurisdiction
        else TimeValidityResult(
            valid=False,
            status="uncertain",
            reason="Title has no jurisdiction_id; cannot evaluate time-based validity.",
        )
    )

    jurisdiction_rules = (
        check_jurisdiction_rules(title_rank=title.rank, jurisdiction=jurisdiction)
        if jurisdiction
        else JurisdictionRuleCheck(
            allowed=False,
            conditions=["No jurisdiction assigned to this title."],
            requirements=[],
        )
    )

    succession: SuccessionEvaluationResult | None = None
    if title.grantor_person_id:
        if jurisdiction:
            payload = _succession_payload_from_jurisdiction(
                jurisdiction, root_id=title.grantor_person_id, candidate_id=person_id, as_of=as_of
            )
        else:
            payload = SuccessionEvaluationRequest(
                root_person_id=title.grantor_person_id,
                candidate_person_id=person_id,
                rule_type="agnatic",
                as_of=as_of,
            )
        succession = evaluate_succession(db, payload)

    # Compute validity/confidence deterministically from components.
    has_genealogy_errors = any(i.severity == "error" for i in genealogy.issues)
    succession_status = succession.status if succession else "UNCERTAIN"

    valid = (
        not has_genealogy_errors
        and time_validity.valid
        and jurisdiction_rules.allowed
        and succession_status == "VALID"
    )

    # Confidence heuristic: do not claim certainty if key inputs missing.
    confidence = 1.0 if valid else 0.5
    if has_genealogy_errors or not time_validity.valid:
        confidence = 0.0
    if succession is None:
        confidence = min(confidence, 0.5)

    sources: set[int] = set(title.source_ids)
    if jurisdiction:
        sources.update(jurisdiction.source_ids)

    result = JurisdictionTitleValidationResult(
        person_id=person_id,
        title_id=title_id,
        jurisdiction=(
            JurisdictionContext(
                id=jurisdiction.id,
                name=jurisdiction.name,
                code=jurisdiction.code,
                legal_system=jurisdiction.legal_system,
                nobility_abolished_date=jurisdiction.nobility_abolished_date,
                legal_references=jurisdiction.legal_references,
            )
            if jurisdiction
            else None
        ),
        time_validity=time_validity,
        jurisdiction_rules=jurisdiction_rules,
        genealogy=genealogy,
        succession=succession,
        valid=valid,
        confidence=confidence,
        sources=sorted(list(sources)),
    )

    # Record audit event with machine-readable payload.
    audit = record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=actor_user_id,
            action="VALIDATE.JURISDICTION_TITLE",
            entity_type="title",
            entity_id=str(title_id),
            metadata={"result": result.model_dump(mode="json")},
        ),
        commit=True,
    )

    return result, audit.id
