from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.service import explain_validation_payload
from app.core.audit import AuditEvent, record_audit_event
from app.core.authority import require_roles
from app.core.database import get_db
from app.orders.models import Order
from app.orders_classifier.service import validate_order
from app.roles.enums import Role
from app.users.models import User
from app.validation.schemas import (
    BatchOrderValidationRequest,
    BatchOrderValidationResponse,
    FraudReportResponse,
    OrderValidationRequest,
    OrderValidationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["orders_validation"])


@router.post("/validate/order", response_model=OrderValidationResponse)
def validate_order_endpoint(
    payload: OrderValidationRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    """Validate a chivalric order's legitimacy using Day 3/4/6 engines + AI explanation."""
    try:
        result, audit_id = validate_order(db, payload=payload, actor_user_id=actor.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Generate AI explanation
    try:
        explanation = explain_validation_payload(
            {
                "kind": "order_validation",
                "result": result.model_dump(mode="json"),
            },
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return OrderValidationResponse(
        result=result,
        explanation=explanation,
        audit_id=audit_id,
    )


@router.post("/orders/batch-validate", response_model=BatchOrderValidationResponse)
def batch_validate_orders_endpoint(
    payload: BatchOrderValidationRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(Role.ADMIN, Role.RESEARCHER)),
):
    """Batch validate multiple orders with the same claimant."""
    results = []
    audit_ids = []

    for order_id in payload.order_ids:
        try:
            req = OrderValidationRequest(
                order_id=order_id,
                claimant_person_id=payload.claimant_person_id,
                as_of=None,
            )
            result, audit_id = validate_order(db, payload=req, actor_user_id=actor.id)
            results.append(result)
            audit_ids.append(audit_id)
        except ValueError:
            # Skip orders that can't be found
            continue

    return BatchOrderValidationResponse(
        results=results,
        audit_ids=audit_ids,
    )


@router.get("/orders/fraud-report", response_model=FraudReportResponse)
def fraud_report_endpoint(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(Role.ADMIN)),
    min_score: int = Query(default=0, ge=0, le=100),
    max_score: int = Query(default=100, ge=0, le=100),
):
    """Generate fraud report dashboard (ADMIN only)."""
    # Query orders with legitimacy scores in range
    query = select(Order).where(
        Order.legitimacy_score.isnot(None),
        Order.legitimacy_score >= min_score,
        Order.legitimacy_score <= max_score,
    )
    orders = db.scalars(query).all()

    # Aggregate by classification
    by_classification: dict[str, int] = {}
    for order in orders:
        if order.classification:
            by_classification[order.classification] = by_classification.get(order.classification, 0) + 1

    # Aggregate by fraud flags
    by_flag: dict[str, int] = {}
    for order in orders:
        if order.fraud_flags:
            for flag in order.fraud_flags:
                by_flag[flag] = by_flag.get(flag, 0) + 1

    # Build order list with key fields
    order_data = [
        {
            "id": o.id,
            "name": o.name,
            "classification": o.classification,
            "legitimacy_score": o.legitimacy_score,
            "fraud_flags": o.fraud_flags or [],
            "last_legitimacy_check": o.last_legitimacy_check.isoformat() if o.last_legitimacy_check else None,
        }
        for o in orders
    ]

    return FraudReportResponse(
        min_score=min_score,
        max_score=max_score,
        total_orders=len(orders),
        by_classification=by_classification,
        by_flag=by_flag,
        orders=order_data,
    )
