from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.health.router import router as health_router
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.audit.router import router as audit_router
from app.users.service import ensure_bootstrap_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Establish first-run authority (optional) without mixing environments.
    ensure_bootstrap_admin()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Royal BrAIn™ API",
        version="0.1.0-day1",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(audit_router)

    return app


app = create_app()
