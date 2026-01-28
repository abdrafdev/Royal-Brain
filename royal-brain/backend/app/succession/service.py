from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.persons.models import Person
from app.relationships.models import Relationship
from app.succession.schemas import (
    CustomRule,
    SuccessionEvaluationRequest,
    SuccessionEvaluationResult,
    SuccessionReason,
)

PARENT_CHILD_TYPES = {"parent_child", "adoption"}


@dataclass(frozen=True)
class RuleConfig:
    allow_female_inheritance: bool
    allow_female_transmission: bool
    allow_adoption: bool
    max_depth: int


def _default_depth(custom: CustomRule | None) -> int:
    if custom and custom.max_depth is not None:
        return custom.max_depth
    return 12


def _config_for_rule(rule_type: str, custom: CustomRule | None) -> RuleConfig:
    if rule_type == "agnatic":
        return RuleConfig(
            allow_female_inheritance=False,
            allow_female_transmission=False,
            allow_adoption=False,
            max_depth=_default_depth(custom),
        )
    if rule_type == "salic":
        return RuleConfig(
            allow_female_inheritance=False,
            allow_female_transmission=False,
            allow_adoption=False,
            max_depth=_default_depth(custom),
        )
    if rule_type == "semi_salic":
        return RuleConfig(
            allow_female_inheritance=False,  # claimant must be male
            allow_female_transmission=True,  # female may transmit if no closer male line
            allow_adoption=False,
            max_depth=_default_depth(custom),
        )
    if rule_type == "cognatic":
        return RuleConfig(
            allow_female_inheritance=True,
            allow_female_transmission=True,
            allow_adoption=True,
            max_depth=_default_depth(custom),
        )

    # custom rule
    cfg = custom or CustomRule()
    return RuleConfig(
        allow_female_inheritance=cfg.allow_female_inheritance,
        allow_female_transmission=cfg.allow_female_transmission,
        allow_adoption=cfg.allow_adoption,
        max_depth=_default_depth(cfg),
    )


def _as_of_clause(as_of: date | None):
    if as_of is None:
        return None
    return and_(
        Relationship.valid_from <= as_of,
        or_(Relationship.valid_to.is_(None), Relationship.valid_to >= as_of),
    )


def _normalize_sex(raw: str | None) -> str | None:
    if raw is None:
        return None
    v = raw.strip().upper()
    if not v:
        return None
    return v


def _load_relationships(
    db: Session, *, as_of: date | None, allow_adoption: bool
) -> list[Relationship]:
    clauses = [
        Relationship.left_entity_type == "person",
        Relationship.right_entity_type == "person",
        Relationship.relationship_type.in_(sorted(PARENT_CHILD_TYPES)),
    ]
    as_of_clause = _as_of_clause(as_of)
    if as_of_clause is not None:
        clauses.append(as_of_clause)

    rels = db.scalars(select(Relationship).where(*clauses)).all()
    if not allow_adoption:
        rels = [r for r in rels if r.relationship_type != "adoption"]
    return rels


def _build_adjacency(
    rels: Iterable[Relationship],
) -> tuple[dict[int, list[Relationship]], dict[tuple[int, int], list[Relationship]]]:
    parent_to_rels: dict[int, list[Relationship]] = defaultdict(list)
    edge_lookup: dict[tuple[int, int], list[Relationship]] = defaultdict(list)
    for r in rels:
        parent_to_rels[r.left_entity_id].append(r)
        edge_lookup[(r.left_entity_id, r.right_entity_id)].append(r)
    return parent_to_rels, edge_lookup


def _find_paths(
    parent_to_rels: dict[int, list[Relationship]],
    root_id: int,
    candidate_id: int,
    max_depth: int,
) -> list[tuple[list[int], list[Relationship]]]:
    paths: list[tuple[list[int], list[Relationship]]] = []
    queue: deque[tuple[list[int], list[Relationship]]] = deque()
    queue.append(([root_id], []))

    while queue:
        persons_path, rels_path = queue.popleft()
        if len(persons_path) - 1 >= max_depth:
            # depth limit reached (edges count = persons -1)
            continue

        last_person = persons_path[-1]
        for rel in parent_to_rels.get(last_person, []):
            child = rel.right_entity_id
            if child in persons_path:
                continue  # avoid cycles

            next_persons = persons_path + [child]
            next_rels = rels_path + [rel]

            if child == candidate_id:
                paths.append((next_persons, next_rels))
            else:
                queue.append((next_persons, next_rels))

    return paths


def _evaluate_path(
    persons_path: list[int],
    rels_path: list[Relationship],
    sexes: dict[int, str | None],
    rule: RuleConfig,
) -> tuple[str, list[SuccessionReason]]:
    reasons: list[SuccessionReason] = []
    status = "VALID"

    # Adoption constraint
    if not rule.allow_adoption:
        for rel in rels_path:
            if rel.relationship_type == "adoption":
                status = "INVALID"
                reasons.append(
                    SuccessionReason(
                        severity="error",
                        code="ADOPTION_NOT_ALLOWED",
                        message="Path includes adoption but rule forbids it.",
                        relationship_id=rel.id,
                    )
                )
                return status, reasons

    # Sex constraints
    candidate_id = persons_path[-1]
    for pid in persons_path:
        sex = sexes.get(pid)

        # Candidate check
        if pid == candidate_id and not rule.allow_female_inheritance:
            if sex is None:
                status = "UNCERTAIN"
                reasons.append(
                    SuccessionReason(
                        severity="warning",
                        code="CANDIDATE_SEX_UNKNOWN",
                        message="Candidate sex is missing; cannot prove male-line succession.",
                        person_id=pid,
                    )
                )
                return status, reasons
            if sex != "M":
                status = "INVALID"
                reasons.append(
                    SuccessionReason(
                        severity="error",
                        code="CANDIDATE_SEX_DISALLOWED",
                        message="Candidate is not male; rule requires male heir.",
                        person_id=pid,
                    )
                )
                return status, reasons

        # Ancestor transmission check
        if pid != candidate_id and not rule.allow_female_transmission:
            if sex is None:
                status = "UNCERTAIN"
                reasons.append(
                    SuccessionReason(
                        severity="warning",
                        code="ANCESTOR_SEX_UNKNOWN",
                        message="Ancestor sex missing; cannot verify strict male-line.",
                        person_id=pid,
                    )
                )
                return status, reasons
            if sex != "M":
                status = "INVALID"
                reasons.append(
                    SuccessionReason(
                        severity="error",
                        code="ANCESTOR_SEX_DISALLOWED",
                        message="Ancestor is not male; rule requires male-line transmission.",
                        person_id=pid,
                    )
                )
                return status, reasons

    return status, reasons


def evaluate_succession(
    db: Session, payload: SuccessionEvaluationRequest
) -> SuccessionEvaluationResult:
    if payload.root_person_id == payload.candidate_person_id:
        raise ValueError("Root and candidate must differ.")

    root = db.get(Person, payload.root_person_id)
    candidate = db.get(Person, payload.candidate_person_id)
    if root is None or candidate is None:
        raise ValueError("Root or candidate person not found.")

    rule_cfg = _config_for_rule(payload.rule_type, payload.custom_rule)
    applied_rule = payload.custom_rule or CustomRule(
        allow_female_inheritance=rule_cfg.allow_female_inheritance,
        allow_female_transmission=rule_cfg.allow_female_transmission,
        allow_adoption=rule_cfg.allow_adoption,
        max_depth=rule_cfg.max_depth,
    )

    rels = _load_relationships(
        db, as_of=payload.as_of, allow_adoption=rule_cfg.allow_adoption
    )
    parent_to_rels, _ = _build_adjacency(rels)

    paths = _find_paths(
        parent_to_rels=parent_to_rels,
        root_id=payload.root_person_id,
        candidate_id=payload.candidate_person_id,
        max_depth=rule_cfg.max_depth,
    )

    if not paths:
        return SuccessionEvaluationResult(
            root_person_id=payload.root_person_id,
            candidate_person_id=payload.candidate_person_id,
            rule_type=payload.rule_type,
            status="INVALID",
            as_of=payload.as_of,
            path_person_ids=None,
            relationship_ids=None,
            checked_paths=0,
            reasons=[
                SuccessionReason(
                    severity="error",
                    code="NO_LINEAGE_PATH",
                    message="No lineage path found from root to candidate within depth limit.",
                )
            ],
            applied_rule=applied_rule,
        )

    # Load all persons involved across candidate paths for sex checks.
    person_ids: set[int] = {pid for path, _ in paths for pid in path}
    people = db.scalars(select(Person).where(Person.id.in_(person_ids))).all()
    sexes: dict[int, str | None] = {p.id: _normalize_sex(p.sex) for p in people}

    checked = 0
    uncertain_paths: list[tuple[list[int], list[Relationship], list[SuccessionReason]]]
    uncertain_paths = []
    invalid_paths: list[tuple[list[int], list[Relationship], list[SuccessionReason]]]
    invalid_paths = []

    for persons_path, rels_path in paths:
        checked += 1
        status, reasons = _evaluate_path(persons_path, rels_path, sexes, rule_cfg)
        if status == "VALID":
            return SuccessionEvaluationResult(
                root_person_id=payload.root_person_id,
                candidate_person_id=payload.candidate_person_id,
                rule_type=payload.rule_type,
                status="VALID",
                as_of=payload.as_of,
                path_person_ids=persons_path,
                relationship_ids=[r.id for r in rels_path],
                checked_paths=checked,
                reasons=reasons,
                applied_rule=applied_rule,
            )
        if status == "UNCERTAIN":
            uncertain_paths.append((persons_path, rels_path, reasons))
        else:
            invalid_paths.append((persons_path, rels_path, reasons))

    if uncertain_paths:
        persons_path, rels_path, reasons = uncertain_paths[0]
        return SuccessionEvaluationResult(
            root_person_id=payload.root_person_id,
            candidate_person_id=payload.candidate_person_id,
            rule_type=payload.rule_type,
            status="UNCERTAIN",
            as_of=payload.as_of,
            path_person_ids=persons_path,
            relationship_ids=[r.id for r in rels_path],
            checked_paths=checked,
            reasons=reasons,
            applied_rule=applied_rule,
        )

    persons_path, rels_path, reasons = invalid_paths[0]
    return SuccessionEvaluationResult(
        root_person_id=payload.root_person_id,
        candidate_person_id=payload.candidate_person_id,
        rule_type=payload.rule_type,
        status="INVALID",
        as_of=payload.as_of,
        path_person_ids=persons_path,
        relationship_ids=[r.id for r in rels_path] if rels_path else None,
        checked_paths=checked,
        reasons=reasons,
        applied_rule=applied_rule,
    )
