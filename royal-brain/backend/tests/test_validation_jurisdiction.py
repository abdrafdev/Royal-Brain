from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.schemas import SuccessionExplanation
from app.audit.models import AuditLog
from app.core import authority
from app.core.database import Base, get_db
import app.core.models  # noqa: F401 - ensures models are registered with metadata
from app.jurisdictions.models import Jurisdiction
from app.persons.models import Person
from app.roles.enums import Role
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User
from app.validation.router import router as validation_router


def _make_sessionmaker():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def _make_app(*, session_maker, current_user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(validation_router)

    def override_get_db():
        db = session_maker()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[authority.get_current_user] = override_get_current_user
    return app


def test_validate_jurisdiction_title_viewer_forbidden():
    SessionLocal = _make_sessionmaker()

    viewer = User(
        email="viewer@example.com",
        hashed_password="x",
        role=Role.VIEWER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=viewer)
    client = TestClient(app)

    resp = client.post("/api/v1/validate/jurisdiction", json={"person_id": 1, "title_id": 1})
    assert resp.status_code == 403


def test_validate_jurisdiction_title_success_records_audit_log():
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    j = Jurisdiction(
        name="Testland",
        code="TL",
        legal_system="custom",
        nobility_abolished_date=None,
        succession_rules_json={"succession_rule_type": "agnatic"},
        recognized_orders=None,
        legal_references=["Test Act 1850"],
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    src = Source(
        source_type="law",
        jurisdiction_id=None,
        issued_date=None,
        citation="Test Act 1850",
        url=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    grantor = Person(
        primary_name="Grantor",
        sex="M",
        names=None,
        birth_date=None,
        death_date=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    claimant = Person(
        primary_name="Claimant",
        sex="M",
        names=None,
        birth_date=None,
        death_date=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    db.add_all([j, src, grantor, claimant])
    db.flush()

    # Attach evidentiary source links.
    j.sources = [src]

    title = Title(
        name="Duke of Test",
        rank="duke",
        granted_date=date(1850, 1, 1),
        grantor_person_id=grantor.id,
        jurisdiction_id=j.id,
        notes=None,
        valid_from=date(1850, 1, 1),
        valid_to=None,
    )
    title.sources = [src]
    db.add(title)
    db.flush()

    # Parent-child link Grantor -> Claimant so succession is deterministically VALID.
    from app.relationships.models import Relationship

    rel = Relationship(
        relationship_type="parent_child",
        left_entity_type="person",
        left_entity_id=grantor.id,
        right_entity_type="person",
        right_entity_id=claimant.id,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )
    db.add(rel)
    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    dummy_expl = SuccessionExplanation(
        summary="Deterministic test explanation.",
        detailed_reasoning="This explanation is mocked for unit testing.",
        citations=[{"category": "other", "description": "mock"}],
    )

    with patch("app.validation.router.explain_validation_payload", return_value=dummy_expl):
        resp = client.post(
            "/api/v1/validate/jurisdiction",
            json={"person_id": claimant.id, "title_id": title.id},
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["result"]["valid"] is True
    assert body["result"]["confidence"] == 1.0
    assert body["explanation"]["summary"] == dummy_expl.summary

    audit_id = body["audit_id"]
    assert isinstance(audit_id, int)

    # Query using a fresh session (the request session is created/closed by the dependency override).
    db2 = SessionLocal()
    try:
        audit = db2.scalar(select(AuditLog).where(AuditLog.id == audit_id))
        assert audit is not None
        assert audit.action == "VALIDATE.JURISDICTION_TITLE"
        assert audit.entity_type == "title"
        assert audit.entity_id == str(title.id)
    finally:
        db2.close()
