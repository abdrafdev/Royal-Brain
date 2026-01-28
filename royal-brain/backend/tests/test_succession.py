from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
import app.core.models  # noqa: F401 - ensures models are registered with metadata
from app.persons.models import Person
from app.relationships.models import Relationship
from app.succession.schemas import SuccessionEvaluationRequest
from app.succession.service import evaluate_succession


def _make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", future=True, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _person(name: str, sex: str | None, valid_from: date = date(1800, 1, 1)) -> Person:
    return Person(
        primary_name=name,
        sex=sex,
        valid_from=valid_from,
        valid_to=None,
    )


def _rel(parent_id: int, child_id: int, rel_type: str = "parent_child") -> Relationship:
    return Relationship(
        relationship_type=rel_type,
        left_entity_type="person",
        left_entity_id=parent_id,
        right_entity_type="person",
        right_entity_id=child_id,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )


def test_agnatic_male_line_valid():
    db = _make_session()
    p1 = _person("Root", "M")
    p2 = _person("Son", "M")
    db.add_all([p1, p2])
    db.flush()
    db.add(_rel(p1.id, p2.id))
    db.commit()

    payload = SuccessionEvaluationRequest(
        root_person_id=p1.id,
        candidate_person_id=p2.id,
        rule_type="agnatic",
    )

    result = evaluate_succession(db, payload)
    assert result.status == "VALID"
    assert result.path_person_ids == [p1.id, p2.id]


def test_agnatic_female_breaks_line():
    db = _make_session()
    p1 = _person("Root", "M")
    p2 = _person("Daughter", "F")
    p3 = _person("Grandson", "M")
    db.add_all([p1, p2, p3])
    db.flush()
    db.add_all([_rel(p1.id, p2.id), _rel(p2.id, p3.id)])
    db.commit()

    payload = SuccessionEvaluationRequest(
        root_person_id=p1.id,
        candidate_person_id=p3.id,
        rule_type="agnatic",
    )

    result = evaluate_succession(db, payload)
    assert result.status == "INVALID"
    assert any(r.code == "ANCESTOR_SEX_DISALLOWED" for r in result.reasons)


def test_semi_salic_allows_female_transmission_to_male_heir():
    db = _make_session()
    p1 = _person("Root", "M")
    p2 = _person("Daughter", "F")
    p3 = _person("Grandson", "M")
    db.add_all([p1, p2, p3])
    db.flush()
    db.add_all([_rel(p1.id, p2.id), _rel(p2.id, p3.id)])
    db.commit()

    payload = SuccessionEvaluationRequest(
        root_person_id=p1.id,
        candidate_person_id=p3.id,
        rule_type="semi_salic",
    )

    result = evaluate_succession(db, payload)
    assert result.status == "VALID"


def test_unknown_sex_returns_uncertain_for_male_line_rule():
    db = _make_session()
    p1 = _person("Root", "M")
    p2 = _person("Child", None)
    db.add_all([p1, p2])
    db.flush()
    db.add(_rel(p1.id, p2.id))
    db.commit()

    payload = SuccessionEvaluationRequest(
        root_person_id=p1.id,
        candidate_person_id=p2.id,
        rule_type="agnatic",
    )

    result = evaluate_succession(db, payload)
    assert result.status == "UNCERTAIN"
    assert any(r.code == "CANDIDATE_SEX_UNKNOWN" for r in result.reasons)
