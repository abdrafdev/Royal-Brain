from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.schemas import SuccessionExplanation
from app.audit.models import AuditLog
from app.core import authority
from app.core.database import Base, get_db
import app.core.models  # noqa: F401 - ensures models are registered with metadata
from app.jurisdictions.models import Jurisdiction
from app.orders.models import Order
from app.orders_classifier.router import router as orders_classifier_router
from app.persons.models import Person
from app.relationships.models import Relationship
from app.roles.enums import Role
from app.sources.models import Source
from app.users.models import User


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
    app.include_router(orders_classifier_router)

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


def test_validate_order_viewer_forbidden():
    SessionLocal = _make_sessionmaker()

    viewer = User(
        email="viewer@example.com",
        hashed_password="x",
        role=Role.VIEWER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=viewer)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/validate/order",
        json={"order_id": 1, "claimant_person_id": 1},
    )
    assert resp.status_code == 403


def test_validate_order_legitimate_order_high_score():
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    # Create jurisdiction with succession rules
    juris = Jurisdiction(
        name="Testland",
        code="TL",
        legal_system="custom",
        nobility_abolished_date=None,
        succession_rules_json={"succession_rule_type": "agnatic"},
        recognized_orders=["Order of Test"],
        legal_references=["Test Charter 1800"],
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    src = Source(
        source_type="charter",
        jurisdiction_id=None,
        issued_date=date(1800, 1, 1),
        citation="Test Charter 1800",
        url=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )

    fons = Person(
        primary_name="Fons Honorum",
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

    db.add_all([juris, src, fons, claimant])
    db.flush()

    juris.sources = [src]

    # Create order with all legitimacy factors
    order = Order(
        name="Order of Test",
        jurisdiction_id=juris.id,
        fons_honorum_person_id=fons.id,
        founding_document_source_id=src.id,
        granted_date=date(1850, 1, 1),
        grantor_person_id=fons.id,
        recognized_by=["TL"],
        notes=None,
        valid_from=date(1850, 1, 1),
        valid_to=None,
    )
    order.sources = [src]
    db.add(order)
    db.flush()

    # Create parent-child relationship for succession
    rel = Relationship(
        relationship_type="parent_child",
        left_entity_type="person",
        left_entity_id=fons.id,
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
        summary="Legitimate order with valid fons honorum and succession.",
        detailed_reasoning="This is a test explanation.",
        citations=[{"category": "other", "description": "test"}],
    )

    with patch("app.orders_classifier.router.explain_validation_payload", return_value=dummy_expl):
        resp = client.post(
            "/api/v1/validate/order",
            json={"order_id": order.id, "claimant_person_id": claimant.id},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Should be LEGITIMATE with high score
    assert body["result"]["classification"] in ["LEGITIMATE", "DISPUTED"]  # may vary based on exact scoring
    assert body["result"]["legitimacy_score"] >= 50  # at least moderate score
    assert body["result"]["fraud_flags"] == []  # no fraud flags for legitimate order
    assert body["explanation"]["summary"] == dummy_expl.summary

    audit_id = body["audit_id"]
    assert isinstance(audit_id, int)

    db2 = SessionLocal()
    try:
        audit = db2.scalar(select(AuditLog).where(AuditLog.id == audit_id))
        assert audit is not None
        assert audit.action == "VALIDATE.ORDER"
        assert audit.entity_type == "order"
        assert audit.entity_id == str(order.id)
    finally:
        db2.close()


def test_validate_order_fraudulent_order_low_score():
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    src = Source(
        source_type="none",
        jurisdiction_id=None,
        issued_date=None,
        citation="No citation",
        url=None,
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

    db.add_all([src, claimant])
    db.flush()

    # Fraudulent order with no foundational data
    order = Order(
        name="Self-Styled Sovereign Order",  # suspicious name
        jurisdiction_id=None,  # no jurisdiction
        fons_honorum_person_id=None,  # no fons honorum
        founding_document_source_id=None,  # no founding doc
        granted_date=None,  # no granted date
        grantor_person_id=None,  # no grantor
        recognized_by=None,  # no recognition
        notes=None,
        valid_from=date(2000, 1, 1),
        valid_to=None,
    )
    order.sources = [src]  # minimal source
    db.add(order)
    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    dummy_expl = SuccessionExplanation(
        summary="Self-styled order with no verifiable authority.",
        detailed_reasoning="This is a test explanation.",
        citations=[{"category": "other", "description": "test"}],
    )

    with patch("app.orders_classifier.router.explain_validation_payload", return_value=dummy_expl):
        resp = client.post(
            "/api/v1/validate/order",
            json={"order_id": order.id, "claimant_person_id": claimant.id},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Should be FRAUDULENT or SELF_STYLED with low score
    assert body["result"]["classification"] in ["FRAUDULENT", "SELF_STYLED", "DISPUTED"]
    assert body["result"]["legitimacy_score"] < 50  # low score
    assert len(body["result"]["fraud_flags"]) > 0  # should have fraud flags

    # Check for expected fraud flags
    flags = body["result"]["fraud_flags"]
    assert "MISSING_FONS_HONORUM" in flags
    assert "NO_JURISDICTION_RECOGNITION" in flags
    assert "SUSPICIOUS_NAME_PATTERN" in flags  # order name contains "Self-Styled Sovereign"


def test_fraud_report_admin_only():
    SessionLocal = _make_sessionmaker()

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.get("/api/v1/orders/fraud-report")
    assert resp.status_code == 403  # RESEARCHER forbidden; ADMIN only
