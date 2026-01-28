from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.health.router import router as health_router
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.audit.router import router as audit_router

# Day 2 domain routers
from app.sources.router import router as sources_router
from app.jurisdictions.router import router as jurisdictions_router
from app.persons.router import router as persons_router
from app.families.router import router as families_router
from app.relationships.router import router as relationships_router
from app.orders.router import router as orders_router
from app.titles.router import router as titles_router
from app.heraldic_entities.router import router as heraldic_entities_router

# Day 3 engine routers
from app.genealogy.router import router as genealogy_router

# Day 4 succession router
from app.succession.router import router as succession_router

# Day 5 AI explainability router
from app.ai.router import router as ai_router

# Day 6 validation router
from app.validation.router import router as validation_router

# Day 7 orders classifier router
from app.orders_classifier.router import router as orders_classifier_router

# Day 8 heraldry router
from app.heraldry.router import router as heraldry_router

# Day 9 trust & certification router
from app.trust.router import router as trust_router

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
        version="0.9.0-day9",
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

    # Day 2 canonical assertion layer
    app.include_router(sources_router)
    app.include_router(jurisdictions_router)
    app.include_router(persons_router)
    app.include_router(families_router)
    app.include_router(relationships_router)
    app.include_router(orders_router)
    app.include_router(titles_router)
    app.include_router(heraldic_entities_router)

    # Day 3+ engines
    app.include_router(genealogy_router)
    app.include_router(succession_router)
    app.include_router(ai_router)
    app.include_router(validation_router)
    app.include_router(orders_classifier_router)
    app.include_router(heraldry_router)
    app.include_router(trust_router)

    return app


app = create_app()
