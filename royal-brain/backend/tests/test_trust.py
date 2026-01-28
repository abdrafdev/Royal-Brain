"""Tests for Day 9 Trust & Certification Layer."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import authority
from app.core.database import Base, get_db
from app.persons.models import Person
from app.roles.enums import Role
from app.trust.router import router as trust_router
from app.users.models import User

# Import all models to ensure metadata is complete
import app.heraldic_entities.models  # noqa: F401
import app.trust.models  # noqa: F401
import app.audit.models  # noqa: F401
import app.sources.models  # noqa: F401
import app.titles.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.families.models  # noqa: F401
import app.relationships.models  # noqa: F401
import app.jurisdictions.models  # noqa: F401


def _make_sessionmaker():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _make_app(*, session_maker, current_user: User) -> FastAPI:
    """Create test app with mocked dependencies."""
    app = FastAPI()
    app.include_router(trust_router)
    
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


def test_compute_person_hash():
    """Test computing hash for a person entity."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    # Create test person
    person = Person(
        primary_name="John Doe",
        sex="M",
        valid_from=date(1980, 1, 1),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    
    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )
    
    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)
    
    resp = client.post(
        "/api/v1/trust/hash",
        json={"entity_type": "Person", "entity_id": person.id},
    )
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Person"
    assert body["entity_id"] == person.id
    assert body["hash_algorithm"] == "sha256"
    assert len(body["hash_value"]) == 64  # SHA256 hex length


def test_compute_title_hash():
    """Test computing hash for a title entity."""
    from app.titles.models import Title

    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    title = Title(
        name="Duke of Testshire",
        rank="DUKE",
        valid_from=date(1900, 1, 1),
    )
    db.add(title)
    db.commit()
    db.refresh(title)

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/trust/hash",
        json={"entity_type": "Title", "entity_id": title.id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Title"
    assert body["entity_id"] == title.id
    assert len(body["hash_value"]) == 64


def test_compute_order_hash():
    """Test computing hash for an order entity."""
    from app.orders.models import Order

    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    order = Order(
        name="Most Noble Order of Tests",
        valid_from=date(1950, 1, 1),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/trust/hash",
        json={"entity_type": "Order", "entity_id": order.id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Order"
    assert body["entity_id"] == order.id
    assert len(body["hash_value"]) == 64


def test_compute_family_hash():
    """Test computing hash for a family entity."""
    from app.families.models import Family

    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    family = Family(
        name="House of Testing",
        valid_from=date(1700, 1, 1),
    )
    db.add(family)
    db.commit()
    db.refresh(family)

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/trust/hash",
        json={"entity_type": "Family", "entity_id": family.id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Family"
    assert body["entity_id"] == family.id
    assert len(body["hash_value"]) == 64


def test_compute_heraldic_entity_hash():
    """Test computing hash for a heraldic entity."""
    from app.heraldic_entities.models import HeraldicEntity

    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    heraldic = HeraldicEntity(
        name="Arms of Testing",
        blazon="Azure, a bend Or",
        valid_from=date(1600, 1, 1),
    )
    db.add(heraldic)
    db.commit()
    db.refresh(heraldic)

    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )

    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/trust/hash",
        json={"entity_type": "HeraldicEntity", "entity_id": heraldic.id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "HeraldicEntity"
    assert body["entity_id"] == heraldic.id
    assert len(body["hash_value"]) == 64


def test_get_entity_hash():
    """Test retrieving latest hash for entity."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    person = Person(
        primary_name="Jane Doe",
        sex="F",
        valid_from=date(2000, 1, 1),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    
    # Compute hash first
    from app.trust.hashing import hash_person
    entity_hash = hash_person(db, person.id, user_id=None)
    
    viewer = User(
        email="viewer@example.com",
        hashed_password="x",
        role=Role.VIEWER,
        is_active=True,
    )
    
    app = _make_app(session_maker=SessionLocal, current_user=viewer)
    client = TestClient(app)
    
    resp = client.get(f"/api/v1/trust/hash/Person/{person.id}")
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["hash_value"] == entity_hash.hash_value


def test_generate_certificate():
    """Test generating verification certificate."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    
    person = Person(
        primary_name="Test Person",
        sex="M",
        valid_from=date(2000, 1, 1),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    db.refresh(admin)
    
    # Compute hash first
    from app.trust.hashing import hash_person
    hash_person(db, person.id, user_id=admin.id)
    
    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)
    
    with patch("app.trust.certificates.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/trust/certificate",
            json={
                "entity_type": "Person",
                "entity_id": person.id,
                "certificate_type": "standard",
                "verification_status": "VALID",
                "confidence_score": 0.95,
                "sources_used": [{"name": "Test Source", "type": "document"}],
                "rules_applied": [{"rule_name": "Test Rule", "result": "passed"}],
            },
        )
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Person"
    assert body["entity_id"] == person.id
    assert body["verification_status"] == "VALID"
    assert body["confidence_score"] == 0.95
    assert "ai_explanation" in body


def test_generate_certificate_family_uses_name_field():
    """Regression test: Family certificates should use Family.name (not surname)."""
    from app.families.models import Family

    SessionLocal = _make_sessionmaker()
    db = SessionLocal()

    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()

    family = Family(
        name="House of Cert Testing",
        valid_from=date(1800, 1, 1),
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    db.refresh(admin)

    from app.trust.hashing import hash_family
    hash_family(db, family.id, user_id=admin.id)

    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)

    with patch("app.trust.certificates.get_openai_client", return_value=None):
        resp = client.post(
            "/api/v1/trust/certificate",
            json={
                "entity_type": "Family",
                "entity_id": family.id,
                "certificate_type": "standard",
                "verification_status": "VALID",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Family"
    assert body["entity_id"] == family.id
    assert body["certificate_json"]["entity_name"] == "House of Cert Testing"


def test_anchor_single_hash():
    """Test anchoring single hash to blockchain."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    
    person = Person(
        primary_name="Anchor Test",
        sex="M",
        valid_from=date(2000, 1, 1),
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    db.refresh(admin)
    
    from app.trust.hashing import hash_person
    entity_hash = hash_person(db, person.id, user_id=admin.id)
    
    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)
    
    dummy_tx_hash = "0x" + ("11" * 32)
    dummy_explorer = f"https://example.test/tx/{dummy_tx_hash}"

    with patch(
        "app.trust.blockchain._send_anchor_tx",
        return_value=(dummy_tx_hash, None, None, dummy_explorer),
    ):
        resp = client.post(
            "/api/v1/trust/anchor",
            json={
                "hash_ids": [entity_hash.id],
                "blockchain_network": "polygon-mumbai",
                "batch_mode": False,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["hash_id"] == entity_hash.id
    assert body[0]["blockchain_network"] == "polygon-mumbai"
    assert body[0]["anchor_type"] == "single"
    assert body[0]["transaction_hash"] == dummy_tx_hash
    assert body[0]["explorer_url"] == dummy_explorer


def test_anchor_batch_hashes():
    """Test batch anchoring with Merkle tree."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    
    # Create multiple entities
    person1 = Person(primary_name="Person 1", sex="M", valid_from=date(2000, 1, 1))
    person2 = Person(primary_name="Person 2", sex="F", valid_from=date(2000, 1, 1))
    db.add_all([person1, person2])
    db.commit()
    db.refresh(admin)
    
    from app.trust.hashing import hash_person
    hash1 = hash_person(db, person1.id, user_id=admin.id)
    hash2 = hash_person(db, person2.id, user_id=admin.id)
    
    app = _make_app(session_maker=SessionLocal, current_user=admin)
    client = TestClient(app)
    
    dummy_tx_hash = "0x" + ("22" * 32)
    dummy_explorer = f"https://example.test/tx/{dummy_tx_hash}"

    with patch(
        "app.trust.blockchain._send_anchor_tx",
        return_value=(dummy_tx_hash, None, None, dummy_explorer),
    ):
        resp = client.post(
            "/api/v1/trust/anchor",
            json={
                "hash_ids": [hash1.id, hash2.id],
                "blockchain_network": "polygon-mumbai",
                "batch_mode": True,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["anchor_type"] == "batch"
    assert body[0]["merkle_root"] is not None
    assert body[0]["batch_id"] is not None
    assert body[0]["batch_id"] == body[1]["batch_id"]  # Same batch
    assert body[0]["transaction_hash"] == dummy_tx_hash


def test_verify_anchor():
    """Test verifying blockchain anchor."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    person = Person(primary_name="Verify Test", sex="M", valid_from=date(2000, 1, 1))
    db.add(person)
    db.commit()
    
    from app.trust.hashing import hash_person
    from app.trust.blockchain import anchor_single_hash

    entity_hash = hash_person(db, person.id, user_id=None)

    with patch(
        "app.trust.blockchain._send_anchor_tx",
        return_value=("0x" + ("33" * 32), None, None, None),
    ):
        anchor = anchor_single_hash(db, hash_id=entity_hash.id, user_id=1)
    
    viewer = User(
        email="viewer@example.com",
        hashed_password="x",
        role=Role.VIEWER,
        is_active=True,
    )
    
    app = _make_app(session_maker=SessionLocal, current_user=viewer)
    client = TestClient(app)
    
    from types import SimpleNamespace

    dummy_settings = SimpleNamespace(
        evm_rpc_url="http://example.invalid",
        evm_chain_id=None,
        evm_private_key=None,
        evm_explorer_tx_url_base=None,
    )

    with patch("app.trust.blockchain.get_settings", return_value=dummy_settings), patch(
        "web3.Web3"
    ) as MockWeb3:
        w3 = MockWeb3.return_value
        w3.is_connected.return_value = True
        w3.eth.get_transaction_receipt.side_effect = Exception("not found")
        MockWeb3.HTTPProvider.return_value = object()

        resp = client.get(f"/api/v1/trust/anchor/verify/{anchor.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["anchor_id"] == anchor.id
    assert body["verified"] is False
    assert body["confirmation_status"] == "PENDING"


def test_full_verification_endpoint():
    """Test full verification endpoint with complete entity info."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    admin = User(
        email="admin@example.com",
        hashed_password="x",
        role=Role.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    
    person = Person(primary_name="Full Verification Test", sex="M", valid_from=date(2000, 1, 1))
    db.add(person)
    db.commit()
    db.refresh(person)
    db.refresh(admin)
    
    # Compute hash
    from app.trust.hashing import hash_person
    entity_hash = hash_person(db, person.id, user_id=admin.id)
    
    # Generate certificate
    from app.trust.certificates import generate_certificate, VerificationStatus
    certificate = generate_certificate(
        db,
        entity_type="Person",
        entity_id=person.id,
        certificate_type="standard",
        user_id=admin.id,
        verification_status=VerificationStatus.VALID,
    )
    
    # Anchor to blockchain
    from app.trust.blockchain import anchor_single_hash
    with patch(
        "app.trust.blockchain._send_anchor_tx",
        return_value=("0x" + ("44" * 32), None, None, None),
    ):
        anchor_single_hash(db, hash_id=entity_hash.id, user_id=admin.id)
    
    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )
    
    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    client = TestClient(app)
    
    resp = client.get(f"/api/v1/trust/verify/Person/{person.id}")
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_type"] == "Person"
    assert body["entity_id"] == person.id
    assert body["entity_name"] == "Full Verification Test"
    assert "current_hash" in body
    assert body["current_hash"]["hash_value"] == entity_hash.hash_value
    assert body["certificate"] is not None
    assert body["certificate"]["id"] == certificate.id
    assert body["blockchain_anchor"] is not None
    assert "audit_trail" in body


def test_rbac_admin_only_anchoring():
    """Test that only ADMIN can anchor to blockchain."""
    SessionLocal = _make_sessionmaker()
    db = SessionLocal()
    
    person = Person(primary_name="RBAC Test", sex="M", valid_from=date(2000, 1, 1))
    db.add(person)
    db.commit()
    
    from app.trust.hashing import hash_person
    entity_hash = hash_person(db, person.id, user_id=None)
    
    # Try as RESEARCHER (should fail)
    researcher = User(
        email="researcher@example.com",
        hashed_password="x",
        role=Role.RESEARCHER,
        is_active=True,
    )
    
    app = _make_app(session_maker=SessionLocal, current_user=researcher)
    
    # Override to simulate RESEARCHER without ADMIN access
    def override_researcher():
        return researcher
    app.dependency_overrides[authority.get_current_user] = override_researcher
    
    client = TestClient(app)
    
    resp = client.post(
        "/api/v1/trust/anchor",
        json={"hash_ids": [entity_hash.id], "batch_mode": False},
    )
    
    assert resp.status_code == 403
