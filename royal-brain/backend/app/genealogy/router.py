from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authority import require_roles
from app.core.database import get_db
from app.genealogy.schemas import Direction, GenealogyCheckResponse, GenealogyTreeResponse
from app.genealogy.service import build_person_tree, check_timeline_consistency
from app.roles.enums import Role
from app.users.models import User

router = APIRouter(prefix="/genealogy", tags=["genealogy"])


@router.get("/persons/{person_id}/tree", response_model=GenealogyTreeResponse)
def get_person_tree(
    person_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    direction: Direction = "ancestors",
    depth: int = 4,
    as_of: date | None = None,
    include_marriages: bool = True,
):
    depth = max(1, min(depth, 10))

    try:
        return build_person_tree(
            db,
            root_person_id=person_id,
            direction=direction,
            depth=depth,
            as_of=as_of,
            include_marriages=include_marriages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/persons/{person_id}/checks", response_model=GenealogyCheckResponse)
def get_person_checks(
    person_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER, Role.VIEWER)),
    depth: int = 4,
    as_of: date | None = None,
):
    depth = max(1, min(depth, 10))

    try:
        return check_timeline_consistency(db, root_person_id=person_id, depth=depth, as_of=as_of)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
