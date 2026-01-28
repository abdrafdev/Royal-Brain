"""Day 8 Heraldry tests — Comprehensive backend validation."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit.models import AuditLog
from app.core import authority
from app.core.database import Base, get_db
import app.core.models  # noqa: F401
from app.heraldic_entities.models import HeraldicEntity
from app.heraldry.router import router as heraldry_router
from app.jurisdictions.models import Jurisdiction
from app.persons.models import Person
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
    app.include_router(heraldry_router)

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


def test_parse_blazon_viewer_forbidden():
    """VIEWER role should be forbidden from parsing blazons."""
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
        "/api/v1/heraldry/parse",
        json={"blazon": "Gules, a lion rampant Or"},
    )
    assert resp.status_code == 403


def test_parse_blazon_valid():
    """Parse a valid blazon successfully."""
    SessionLocal = _make_sessionmaker()

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/heraldry/parse",
        json={"blazon": "Gules, a lion rampant Or"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["field_tincture"] == "Gules"
    assert body["field_tincture_type"] == "color"
    assert body["valid"] is True
    assert len(body["charges"]) == 1
    assert body["charges"][0]["name"] == "lion"
    assert body["charges"][0]["tincture"] == "Or"


def test_parse_blazon_invalid_tincture():
    """Parse blazon with invalid tincture should return errors."""
    SessionLocal = _make_sessionmaker()

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/heraldry/parse",
        json={"blazon": "InvalidColor, a lion rampant Or"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["valid"] is False
    assert len(body["errors"]) > 0


def test_validate_heraldry_rule_of_tincture_violation():
    """Validate blazon that violates Rule of Tincture."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    # Create jurisdiction
    juris = Jurisdiction(
        name="Testland",
        code="TL",
        legal_system="custom",
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )
    db.add(juris)
    db.flush()

    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    # Metal on metal (Or on Argent)
    with patch("app.heraldry.service.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/heraldry/validate",
            json={
                "blazon": "Argent, a lion rampant Or",
                "jurisdiction_id": juris.id,
                "generate_svg": False,
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["overall_valid"] is False
    assert len(body["rule_validation"]["violations"]) > 0
    assert any("Rule of Tincture" in v["rule_name"] for v in body["rule_validation"]["violations"])

    # Explainability completeness
    assert "confidence" in body["explanation"]
    assert body["explanation"]["confidence"] == 0.0
    assert "sources" in body["explanation"]
    assert isinstance(body["explanation"]["sources"], list)
    assert "rules_applied" in body["explanation"]
    assert body["explanation"]["rules_applied"]["overall_valid"] is False
    assert body["explanation"]["rules_applied"]["strict_mode"] is True


def test_validate_heraldry_valid_arms():
    """Validate properly formatted blazon that passes all rules."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    juris = Jurisdiction(
        name="Testland",
        code="TL",
        legal_system="custom",
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )
    db.add(juris)
    db.flush()

    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    # Valid: Color field with metal charge
    with patch("app.heraldry.service.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/heraldry/validate",
            json={
                "blazon": "Gules, a lion rampant Or",
                "jurisdiction_id": juris.id,
                "generate_svg": True,
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    assert body["overall_valid"] is True
    assert body["parsed_blazon"]["valid"] is True
    assert body["rule_validation"]["valid"] is True
    assert body["svg"] is not None  # SVG should be generated for valid arms


def test_audit_logging():
    """Verify audit log is created for heraldry validation."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    juris = Jurisdiction(
        name="Testland",
        code="TL",
        legal_system="custom",
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )
    db.add(juris)
    db.flush()
    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    with patch("app.heraldry.service.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/heraldry/validate",
            json={
                "blazon": "Gules, a lion rampant Or",
                "jurisdiction_id": juris.id,
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    # Check audit log was created
    audit_id = body["audit_id"]
    assert isinstance(audit_id, int)

    audit_log = db.get(AuditLog, audit_id)
    assert audit_log is not None
    assert audit_log.action == "VALIDATE.HERALDRY"
    assert audit_log.entity_type == "heraldic_entity"


def test_jurisdiction_compliance_british():
    """Test British heraldic law compliance (royal symbols forbidden)."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)

    juris = Jurisdiction(
        name="United Kingdom",
        code="GB",
        legal_system="common_law",
        jurisdiction_type=None,
        parent_id=None,
        notes=None,
        valid_from=date(1066, 1, 1),
        valid_to=None,
    )
    db.add(juris)
    db.flush()
    db.commit()

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    # Blazon with royal crown
    with patch("app.heraldry.service.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/heraldry/validate",
            json={
                "blazon": "Gules, a crown Or",
                "jurisdiction_id": juris.id,
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    # Should have jurisdiction violations for royal symbol
    juris_comp = body["jurisdiction_compliance"]
    assert juris_comp["compliant"] is False
    assert any("crown" in v.lower() for v in juris_comp["violations"])
