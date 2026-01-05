from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.roles.enums import Role
from app.users.models import User


def get_user_by_email(db: Session, *, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: Session, *, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: Role,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("User already exists") from exc

    db.refresh(user)
    return user


def ensure_bootstrap_admin() -> None:
    """Optionally creates an initial ADMIN from env vars.

    This is the Day 1 establishment of authority.
    """

    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return

    db = SessionLocal()
    try:
        existing = get_user_by_email(db, email=settings.bootstrap_admin_email)
        if existing:
            return

        admin = create_user(
            db,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            role=Role.ADMIN,
        )

        record_audit_event(
            db,
            event=AuditEvent(
                actor_user_id=None,
                action="SYSTEM.BOOTSTRAP_ADMIN_CREATED",
                entity_type="user",
                entity_id=str(admin.id),
                metadata={"email": admin.email},
            ),
        )
    except OperationalError:
        # DB schema likely not migrated yet.
        return
    finally:
        db.close()
