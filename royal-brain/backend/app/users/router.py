from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.audit import AuditEvent, record_audit_event
from app.core.database import get_db
from app.roles.enums import Role
from app.users.models import User
from app.users.schemas import UserCreate, UserRead, UserUpdate
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


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    users = db.query(User).all()
    return users


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=admin.id,
            action="USER.UPDATED",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"updates": payload.model_dump(exclude_none=True)},
        ),
    )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(Role.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=admin.id,
            action="USER.DELETED",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"email": user.email},
        ),
    )

    db.delete(user)
    db.commit()
