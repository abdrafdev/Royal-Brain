"""Model import aggregator.

Alembic needs a single metadata reference that imports all models.
"""

from app.core.database import Base
from app.users.models import User  # noqa: F401
from app.audit.models import AuditLog  # noqa: F401


target_metadata = Base.metadata
