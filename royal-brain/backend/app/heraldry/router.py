"""Heraldry Router — Day 8 API endpoints with RBAC and audit logging."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.database import get_db
from app.heraldry.blazon_parser import parse_blazon
from app.heraldry.schemas import (
    HeraldryParseRequest,
    HeraldryFullValidationRequest,
    FullValidationResponse,
    ParsedBlazonResponse,
)
from app.heraldry.service import full_heraldic_validation
from app.roles.enums import Role
from app.users.models import User

router = APIRouter(prefix="/api/v1/heraldry", tags=["heraldry"])


@router.post("/parse", response_model=ParsedBlazonResponse)
def parse_blazon_endpoint(
    payload: HeraldryParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
) -> ParsedBlazonResponse:
    """Parse a blazon into structured representation.
    
    RBAC: ADMIN, RESEARCHER required
    """
    
    parsed = parse_blazon(payload.blazon)
    
    return ParsedBlazonResponse(
        field_tincture=parsed.field_tincture,
        field_tincture_type=parsed.field_tincture_type.value,
        charges=parsed.charges,
        ordinaries=parsed.ordinaries,
        partitions=parsed.partitions,
        valid=parsed.valid,
        errors=parsed.errors,
        raw_blazon=parsed.raw_blazon,
    )


@router.post("/validate", response_model=FullValidationResponse)
def full_validation_endpoint(
    payload: HeraldryFullValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
) -> FullValidationResponse:
    """Perform full heraldic validation with all engines.
    
    Includes:
    - Blazon parsing
    - Rule validation (Rule of Tincture, etc.)
    - Jurisdiction compliance
    - SVG generation (only if valid)
    - AI explanation
    - Audit logging
    
    RBAC: ADMIN, RESEARCHER required
    """
    
    response, audit_id = full_heraldic_validation(
        db,
        payload=payload,
        actor_user_id=current_user.id,
    )
    
    return response


@router.get("/entity/{entity_id}/svg")
def get_svg_endpoint(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
) -> dict:
    """Retrieve cached SVG for a heraldic entity.
    
    RBAC: All authenticated users
    """
    from app.heraldic_entities.models import HeraldicEntity
    
    entity = db.get(HeraldicEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Heraldic entity not found")
    
    if not entity.svg_cache:
        raise HTTPException(status_code=404, detail="No SVG generated for this entity")
    
    return {
        "entity_id": entity.id,
        "blazon": entity.blazon,
        "svg": entity.svg_cache,
        "validation_status": entity.validation_status,
    }
