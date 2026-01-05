from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.audit import AuditEvent, record_audit_event
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.auth.dependencies import get_current_user
from app.auth.schemas import Token
from app.users.models import User
from app.users.service import get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm uses `username`; we treat it as an email.
    user = get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token(subject=str(user.id), role=str(user.role))

    record_audit_event(
        db,
        event=AuditEvent(
            actor_user_id=user.id,
            action="AUTH.LOGIN_SUCCESS",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"email": user.email},
        ),
    )

    return Token(access_token=token)


@router.get("/me")
def read_auth_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}
