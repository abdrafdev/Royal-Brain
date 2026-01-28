from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.succession.schemas import (
    SuccessionEvaluationRequest,
    SuccessionEvaluationResult,
)
from app.succession.service import evaluate_succession
from app.users.models import User

router = APIRouter(prefix="/succession", tags=["succession"])


@router.post("/evaluate", response_model=SuccessionEvaluationResult)
def evaluate_succession_endpoint(
    payload: SuccessionEvaluationRequest,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
):
    try:
        return evaluate_succession(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
