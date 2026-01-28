"""Cryptographic Hashing Engine — Day 9.

Deterministic hashing for core entities.

Important properties:
- Canonical JSON serialization (sorted keys, stable formatting)
- No hidden DB writes during verification (verify should be side-effect free)
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.trust.models import EntityHash


def _serialize_date(obj: Any) -> str:
    """Serialize dates/datetimes to ISO format."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _canonical_json(data: dict) -> str:
    """Convert dict to canonical JSON (sorted keys, no whitespace)."""
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_serialize_date,
    )


def _compute_hash(canonical_json: str, algorithm: str = "sha256") -> str:
    """Compute hash of canonical JSON."""
    if algorithm == "sha256":
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    if algorithm == "sha3-256":
        return hashlib.sha3_256(canonical_json.encode("utf-8")).hexdigest()
    raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def _relationship_payload(db: Session, *, person_id: int) -> list[dict[str, Any]]:
    """Return all relationships touching a person, in deterministic order."""
    from app.relationships.models import Relationship

    rels = db.scalars(
        select(Relationship).where(
            or_(
                and_(
                    Relationship.left_entity_type == "person",
                    Relationship.left_entity_id == person_id,
                ),
                and_(
                    Relationship.right_entity_type == "person",
                    Relationship.right_entity_id == person_id,
                ),
            )
        )
    ).all()
    rels.sort(key=lambda r: r.id)

    payload: list[dict[str, Any]] = []
    for r in rels:
        payload.append(
            {
                "id": r.id,
                "relationship_type": r.relationship_type,
                "left_entity_type": r.left_entity_type,
                "left_entity_id": r.left_entity_id,
                "right_entity_type": r.right_entity_type,
                "right_entity_id": r.right_entity_id,
                "notes": r.notes,
                "valid_from": r.valid_from,
                "valid_to": r.valid_to,
                "source_ids": sorted(r.source_ids),
            }
        )

    return payload


def _person_data(db: Session, *, person_id: int) -> dict[str, Any]:
    from app.persons.models import Person

    person = db.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person {person_id} not found")

    return {
        "entity_type": "Person",
        "entity_id": person.id,
        "primary_name": person.primary_name,
        "sex": person.sex,
        "names": person.names,
        "birth_date": person.birth_date,
        "death_date": person.death_date,
        "notes": person.notes,
        "valid_from": person.valid_from,
        "valid_to": person.valid_to,
        "source_ids": sorted(person.source_ids),
        "relationships": _relationship_payload(db, person_id=person.id),
    }


def _title_data(db: Session, *, title_id: int) -> dict[str, Any]:
    from app.titles.models import Title

    title = db.get(Title, title_id)
    if title is None:
        raise ValueError(f"Title {title_id} not found")

    return {
        "entity_type": "Title",
        "entity_id": title.id,
        "name": title.name,
        "rank": title.rank,
        "granted_date": title.granted_date,
        "grantor_person_id": title.grantor_person_id,
        "jurisdiction_id": title.jurisdiction_id,
        "notes": title.notes,
        "valid_from": title.valid_from,
        "valid_to": title.valid_to,
        "source_ids": sorted(title.source_ids),
    }


def _order_data(db: Session, *, order_id: int) -> dict[str, Any]:
    from app.orders.models import Order

    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    return {
        "entity_type": "Order",
        "entity_id": order.id,
        "name": order.name,
        "jurisdiction_id": order.jurisdiction_id,
        "classification": order.classification,
        "legitimacy_score": order.legitimacy_score,
        "fons_honorum_person_id": order.fons_honorum_person_id,
        "fraud_flags": sorted(order.fraud_flags or []),
        "recognized_by": sorted(order.recognized_by or []),
        "founding_document_source_id": order.founding_document_source_id,
        "last_legitimacy_check": order.last_legitimacy_check,
        "granted_date": order.granted_date,
        "grantor_person_id": order.grantor_person_id,
        "notes": order.notes,
        "valid_from": order.valid_from,
        "valid_to": order.valid_to,
        "source_ids": sorted(order.source_ids),
    }


def _family_data(db: Session, *, family_id: int) -> dict[str, Any]:
    from app.families.models import Family

    family = db.get(Family, family_id)
    if family is None:
        raise ValueError(f"Family {family_id} not found")

    return {
        "entity_type": "Family",
        "entity_id": family.id,
        "name": family.name,
        "family_type": family.family_type,
        "notes": family.notes,
        "valid_from": family.valid_from,
        "valid_to": family.valid_to,
        "source_ids": sorted(family.source_ids),
    }


def _heraldic_entity_data(db: Session, *, heraldic_entity_id: int) -> dict[str, Any]:
    from app.heraldic_entities.models import HeraldicEntity

    entity = db.get(HeraldicEntity, heraldic_entity_id)
    if entity is None:
        raise ValueError(f"HeraldicEntity {heraldic_entity_id} not found")

    return {
        "entity_type": "HeraldicEntity",
        "entity_id": entity.id,
        "name": entity.name,
        "jurisdiction_id": entity.jurisdiction_id,
        "blazon": entity.blazon,
        "notes": entity.notes,
        "parsed_structure": entity.parsed_structure,
        "validation_status": entity.validation_status,
        "validation_errors": entity.validation_errors,
        "rule_violations": entity.rule_violations,
        "jurisdiction_compliant": entity.jurisdiction_compliant,
        "jurisdiction_compliance_detail": entity.jurisdiction_compliance_detail,
        "last_validation_check": entity.last_validation_check,
        "claimant_person_id": entity.claimant_person_id,
        "valid_from": entity.valid_from,
        "valid_to": entity.valid_to,
        "source_ids": sorted(entity.source_ids),
    }


def compute_entity_hash_payload(db: Session, *, entity_type: str, entity_id: int) -> dict[str, Any]:
    """Return canonical payload dict for an entity.

    This MUST be deterministic and MUST NOT write to the database.
    """
    if entity_type == "Person":
        return _person_data(db, person_id=entity_id)
    if entity_type == "Title":
        return _title_data(db, title_id=entity_id)
    if entity_type == "Order":
        return _order_data(db, order_id=entity_id)
    if entity_type == "Family":
        return _family_data(db, family_id=entity_id)
    if entity_type == "HeraldicEntity":
        return _heraldic_entity_data(db, heraldic_entity_id=entity_id)

    raise ValueError(f"Unsupported entity type: {entity_type}")


def compute_entity_hash(db: Session, *, entity_type: str, entity_id: int) -> tuple[str, str]:
    """Compute (canonical_json, hash_value) for an entity without persisting."""
    payload = compute_entity_hash_payload(db, entity_type=entity_type, entity_id=entity_id)
    canonical = _canonical_json(payload)
    return canonical, _compute_hash(canonical)


def _persist_hash(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    canonical_json: str,
    hash_value: str,
    hash_algorithm: str,
    user_id: int | None,
) -> EntityHash:
    entity_hash = EntityHash(
        entity_type=entity_type,
        entity_id=entity_id,
        hash_algorithm=hash_algorithm,
        hash_value=hash_value,
        canonical_json=canonical_json,
        computed_by_user_id=user_id,
    )

    db.add(entity_hash)
    db.commit()
    db.refresh(entity_hash)
    return entity_hash


def hash_person(db: Session, person_id: int, *, user_id: int | None = None) -> EntityHash:
    canonical, hash_value = compute_entity_hash(db, entity_type="Person", entity_id=person_id)
    return _persist_hash(
        db,
        entity_type="Person",
        entity_id=person_id,
        canonical_json=canonical,
        hash_value=hash_value,
        hash_algorithm="sha256",
        user_id=user_id,
    )


def hash_title(db: Session, title_id: int, *, user_id: int | None = None) -> EntityHash:
    canonical, hash_value = compute_entity_hash(db, entity_type="Title", entity_id=title_id)
    return _persist_hash(
        db,
        entity_type="Title",
        entity_id=title_id,
        canonical_json=canonical,
        hash_value=hash_value,
        hash_algorithm="sha256",
        user_id=user_id,
    )


def hash_order(db: Session, order_id: int, *, user_id: int | None = None) -> EntityHash:
    canonical, hash_value = compute_entity_hash(db, entity_type="Order", entity_id=order_id)
    return _persist_hash(
        db,
        entity_type="Order",
        entity_id=order_id,
        canonical_json=canonical,
        hash_value=hash_value,
        hash_algorithm="sha256",
        user_id=user_id,
    )


def hash_family(db: Session, family_id: int, *, user_id: int | None = None) -> EntityHash:
    canonical, hash_value = compute_entity_hash(db, entity_type="Family", entity_id=family_id)
    return _persist_hash(
        db,
        entity_type="Family",
        entity_id=family_id,
        canonical_json=canonical,
        hash_value=hash_value,
        hash_algorithm="sha256",
        user_id=user_id,
    )


def hash_heraldic_entity(
    db: Session, heraldic_entity_id: int, *, user_id: int | None = None
) -> EntityHash:
    canonical, hash_value = compute_entity_hash(
        db, entity_type="HeraldicEntity", entity_id=heraldic_entity_id
    )
    return _persist_hash(
        db,
        entity_type="HeraldicEntity",
        entity_id=heraldic_entity_id,
        canonical_json=canonical,
        hash_value=hash_value,
        hash_algorithm="sha256",
        user_id=user_id,
    )


def verify_hash(db: Session, entity_type: str, entity_id: int, hash_value: str) -> bool:
    """Verify that an entity's current state matches a given hash.

    This MUST be side-effect free.
    """
    _canonical, current_hash_value = compute_entity_hash(
        db, entity_type=entity_type, entity_id=entity_id
    )
    return current_hash_value == hash_value


def get_latest_hash(db: Session, entity_type: str, entity_id: int) -> EntityHash | None:
    """Get the most recent hash for an entity."""
    return (
        db.query(EntityHash)
        .filter(EntityHash.entity_type == entity_type, EntityHash.entity_id == entity_id)
        .order_by(EntityHash.timestamp.desc())
        .first()
    )
