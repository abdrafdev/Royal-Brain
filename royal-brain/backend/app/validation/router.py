from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.service import explain_validation_payload
from app.core.authority import require_roles
from app.core.database import get_db
from app.roles.enums import Role
from app.users.models import User
from app.validation.jurisdiction_service import validate_title_claim
from app.validation.schemas import (
    JurisdictionTitleValidationRequest,
    JurisdictionTitleValidationResponse,
)

router = APIRouter(prefix="/api/v1/validate", tags=["validation"])


@router.post("/jurisdiction", response_model=JurisdictionTitleValidationResponse)
def validate_jurisdiction_title(
    payload: JurisdictionTitleValidationRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    try:
        result, audit_id = validate_title_claim(
            db,
            person_id=payload.person_id,
            title_id=payload.title_id,
            actor_user_id=actor.id,
            as_of=payload.as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        explanation = explain_validation_payload(
            {
                "kind": "jurisdiction_title_validation",
                "result": result.model_dump(mode="json"),
            },
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return JurisdictionTitleValidationResponse(
        result=result,
        explanation=explanation,
        audit_id=audit_id,
    )
