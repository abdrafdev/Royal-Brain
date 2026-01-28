"""Model import aggregator.

Alembic needs a single metadata reference that imports all models.
"""

from app.core.database import Base
from app.users.models import User  # noqa: F401
from app.audit.models import AuditLog  # noqa: F401

# Day 2 domain entities
from app.sources.models import Source  # noqa: F401
from app.jurisdictions.models import Jurisdiction  # noqa: F401
from app.persons.models import Person  # noqa: F401
from app.families.models import Family  # noqa: F401
from app.relationships.models import Relationship  # noqa: F401
from app.orders.models import Order  # noqa: F401
from app.titles.models import Title  # noqa: F401
from app.heraldic_entities.models import HeraldicEntity  # noqa: F401


target_metadata = Base.metadata
