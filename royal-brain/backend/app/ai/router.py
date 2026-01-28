from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.schemas import ExplainSuccessionRequest, ExplainSuccessionResponse
from app.ai.service import explain_succession_result
from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.users.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain-succession", response_model=ExplainSuccessionResponse)
def explain_succession_endpoint(
    payload: ExplainSuccessionRequest,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    """Generate human-readable explanation of a succession result using AI."""
    try:
        explanation = explain_succession_result(payload.result, db=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return ExplainSuccessionResponse(
        explanation=explanation,
        raw_result=payload.result,
    )
