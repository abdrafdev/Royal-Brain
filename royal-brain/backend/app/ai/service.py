from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import get_openai_client
from app.ai.prompts import SYSTEM_PROMPT, VALIDATION_PROMPT
from app.ai.schemas import SourceReference, SuccessionExplanation
from app.persons.models import Person
from app.relationships.models import Relationship
from app.sources.models import Source
from app.succession.schemas import SuccessionEvaluationResult


def _call_llm_json(*, system_prompt: str, user_content: dict) -> dict:
    client = get_openai_client()
    if client is None:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in environment.")

    user_message = (
        "Provide an explanation in the required JSON format.\n\nINPUT DATA:\n"
        + json.dumps(user_content, indent=2)
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1500,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("OpenAI returned empty response.")

    return json.loads(raw_content)


def _confidence_for_succession_result(result: SuccessionEvaluationResult) -> float:
    if result.status == "VALID":
        return 1.0
    if result.status == "INVALID":
        return 0.0
    return 0.5


def _rules_for_succession_result(result: SuccessionEvaluationResult) -> dict[str, Any]:
    return {
        "rule_type": result.rule_type,
        "applied_rule": result.applied_rule.model_dump(mode="json"),
    }


def _fallback_succession_explanation(
    result: SuccessionEvaluationResult,
    *,
    confidence: float,
    sources: list[SourceReference],
    rules_applied: dict[str, Any],
    error: str | None = None,
) -> SuccessionExplanation:
    prefix = "AI unavailable; " if error else ""

    summary = (
        f"{prefix}Deterministic explanation: succession status is {result.status} "
        f"under rule_type {result.rule_type}."
    )

    path = (
        " → ".join(str(pid) for pid in result.path_person_ids)
        if result.path_person_ids
        else "(none)"
    )

    reason_lines = []
    for r in result.reasons:
        ctx = []
        if r.person_id is not None:
            ctx.append(f"person_id={r.person_id}")
        if r.relationship_id is not None:
            ctx.append(f"relationship_id={r.relationship_id}")
        ctx_str = f" ({', '.join(ctx)})" if ctx else ""
        reason_lines.append(f"- [{r.severity}] {r.code}: {r.message}{ctx_str}")

    detailed = "\n".join(
        [
            summary,
            "",
            f"root_person_id: {result.root_person_id}",
            f"candidate_person_id: {result.candidate_person_id}",
            f"checked_paths: {result.checked_paths}",
            f"path_person_ids: {path}",
            f"relationship_ids: {', '.join(str(rid) for rid in (result.relationship_ids or [])) or '(none)'}",
            "",
            "reasons:",
            "\n".join(reason_lines) if reason_lines else "(none)",
        ]
    )

    citations: list[dict[str, str]] = [
        {
            "category": "applied_rule",
            "description": "Machine-readable rule context is provided in rules_applied.",
        }
    ]

    if result.status == "UNCERTAIN":
        citations.append(
            {
                "category": "uncertainty",
                "description": "Result is UNCERTAIN based on the provided reasons.",
            }
        )

    if not sources:
        citations.append(
            {
                "category": "uncertainty",
                "description": "No linked Source records were found for the evaluated people/relationships.",
            }
        )

    return SuccessionExplanation(
        summary=summary,
        detailed_reasoning=detailed,
        citations=citations,
        confidence=confidence,
        sources=sources,
        rules_applied=rules_applied,
    )


def _fallback_validation_explanation(
    payload: dict,
    *,
    confidence: float,
    sources: list[SourceReference],
    rules_applied: dict[str, Any],
    error: str | None = None,
) -> SuccessionExplanation:
    kind = payload.get("kind") if isinstance(payload, dict) else None
    prefix = "AI unavailable; " if error else ""

    summary = f"{prefix}Deterministic explanation: {kind or 'validation'} completed."

    detailed_obj = {
        "kind": kind,
        "confidence": confidence,
        "sources": [s.model_dump(mode="json") for s in sources],
        "rules_applied": rules_applied,
    }
    detailed = "This explanation was generated without an LLM.\n\n" + json.dumps(
        detailed_obj, indent=2
    )

    citations: list[dict[str, str]] = [
        {
            "category": "applied_rule",
            "description": "Machine-readable rule context is provided in rules_applied.",
        },
        {
            "category": "other",
            "description": "LLM output was unavailable; explanation generated deterministically.",
        },
    ]

    return SuccessionExplanation(
        summary=summary,
        detailed_reasoning=detailed,
        citations=citations,
        confidence=confidence,
        sources=sources,
        rules_applied=rules_applied,
    )


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


def _sources_for_succession(db: Session, result: SuccessionEvaluationResult) -> list[SourceReference]:
    source_ids: set[int] = set()

    if result.relationship_ids:
        rels = db.scalars(
            select(Relationship).where(Relationship.id.in_(sorted(set(result.relationship_ids))))
        ).all()
        for r in rels:
            source_ids.update(r.source_ids)

    if result.path_person_ids:
        people = db.scalars(
            select(Person).where(Person.id.in_(sorted(set(result.path_person_ids))))
        ).all()
        for p in people:
            source_ids.update(p.source_ids)

    return _source_refs(db, source_ids=sorted(source_ids))


def explain_succession_result(
    result: SuccessionEvaluationResult,
    *,
    db: Session | None = None,
) -> SuccessionExplanation:
    """Generate human-readable explanation of a succession result using OpenAI.

    The returned object is guaranteed to include confidence, sources, and rules_applied.
    """

    rules_applied = _rules_for_succession_result(result)
    confidence = _confidence_for_succession_result(result)
    sources: list[SourceReference] = []
    if db is not None:
        sources = _sources_for_succession(db, result)

    # Prepare structured input for LLM (deterministic-first; no external facts).
    user_content = {
        "status": result.status,
        "rule_type": result.rule_type,
        "root_person_id": result.root_person_id,
        "candidate_person_id": result.candidate_person_id,
        "path_person_ids": result.path_person_ids,
        "relationship_ids": result.relationship_ids,
        "checked_paths": result.checked_paths,
        "reasons": [
            {
                "severity": r.severity,
                "code": r.code,
                "message": r.message,
                "person_id": r.person_id,
                "relationship_id": r.relationship_id,
            }
            for r in result.reasons
        ],
        "applied_rule": rules_applied["applied_rule"],
        "sources": [s.model_dump(mode="json") for s in sources],
        "confidence": confidence,
    }

    try:
        parsed = _call_llm_json(system_prompt=SYSTEM_PROMPT, user_content=user_content)
        explanation = SuccessionExplanation(
            summary=parsed.get("summary", ""),
            detailed_reasoning=parsed.get("detailed_reasoning", ""),
            citations=parsed.get("citations", []),
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
        )

        # If the model returned an incomplete payload, fall back.
        if not explanation.summary or not explanation.detailed_reasoning:
            raise ValueError("LLM returned incomplete explanation")

        return explanation
    except Exception as exc:
        return _fallback_succession_explanation(
            result,
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
            error=str(exc)[:200],
        )


def _confidence_for_validation_payload(payload: dict) -> float:
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        if result.get("confidence") is not None:
            try:
                return float(result["confidence"])
            except Exception:
                pass
        if result.get("legitimacy_score") is not None:
            try:
                return max(0.0, min(1.0, float(result["legitimacy_score"]) / 100.0))
            except Exception:
                pass
    return 0.5


def _sources_for_validation_payload(db: Session, payload: dict) -> list[SourceReference]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return []
    source_ids = result.get("sources")
    if not isinstance(source_ids, list):
        return []
    return _source_refs(db, source_ids=[int(sid) for sid in source_ids if sid is not None])


def _rules_for_validation_payload(payload: dict) -> dict[str, Any]:
    kind = payload.get("kind") if isinstance(payload, dict) else None
    result = payload.get("result") if isinstance(payload, dict) else None
    result = result if isinstance(result, dict) else {}

    if kind == "jurisdiction_title_validation":
        succession = result.get("succession") if isinstance(result.get("succession"), dict) else {}
        return {
            "kind": kind,
            "time_validity": result.get("time_validity"),
            "jurisdiction_rules": result.get("jurisdiction_rules"),
            "succession_applied_rule": succession.get("applied_rule"),
        }

    if kind == "order_validation":
        return {
            "kind": kind,
            "classification": result.get("classification"),
            "legitimacy_score": result.get("legitimacy_score"),
            "fraud_flags": result.get("fraud_flags"),
            "factors": result.get("factors"),
        }

    return {"kind": kind}


def explain_validation_payload(
    payload: dict,
    *,
    db: Session | None = None,
) -> SuccessionExplanation:
    """Explain a generic validation payload (Day 6/7) with strict no-hallucination rules.

    The returned object is guaranteed to include confidence, sources, and rules_applied.
    """
    confidence = _confidence_for_validation_payload(payload)
    rules_applied = _rules_for_validation_payload(payload)

    sources: list[SourceReference] = []
    if db is not None:
        sources = _sources_for_validation_payload(db, payload)

    enriched_payload = dict(payload)
    enriched_payload["confidence"] = confidence
    enriched_payload["sources"] = [s.model_dump(mode="json") for s in sources]
    enriched_payload["rules_applied"] = rules_applied

    try:
        parsed = _call_llm_json(system_prompt=VALIDATION_PROMPT, user_content=enriched_payload)
        explanation = SuccessionExplanation(
            summary=parsed.get("summary", ""),
            detailed_reasoning=parsed.get("detailed_reasoning", ""),
            citations=parsed.get("citations", []),
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
        )

        if not explanation.summary or not explanation.detailed_reasoning:
            raise ValueError("LLM returned incomplete explanation")

        return explanation
    except Exception as exc:
        return _fallback_validation_explanation(
            payload,
            confidence=confidence,
            sources=sources,
            rules_applied=rules_applied,
            error=str(exc)[:200],
        )
