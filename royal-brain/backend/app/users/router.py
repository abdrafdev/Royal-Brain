from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.audit import AuditEvent, record_audit_event
from app.core.database import get_db
from app.roles.enums import Role
from app.users.models import User
from app.users.schemas import UserCreate, UserRead
from app.users.service import create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER))):
    return current_user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    try:
        user = create_user(db, email=payload.email, password=payload.password, role=payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=admin.id,
            action="USER.CREATED",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"email": user.email, "role": str(user.role)},
        ),
    )

    return user
