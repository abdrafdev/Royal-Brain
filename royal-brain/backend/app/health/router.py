from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Liveness probe."""
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.rb_env,
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe (includes DB connectivity)."""
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {str(exc)[:200]}",
        ) from exc

    return {
        "status": "ok",
        "environment": settings.rb_env,
        "database": "ok",
    }
