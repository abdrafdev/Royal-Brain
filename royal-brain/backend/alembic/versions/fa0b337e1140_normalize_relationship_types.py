"""normalize relationship types

Revision ID: fa0b337e1140
Revises: 7a1ca4443bc2
Create Date: 2026-01-26 23:17:46.203269

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "fa0b337e1140"
down_revision = "7a1ca4443bc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize all relationship_type values to canonical lowercase snake_case.
    # This is a data migration only; schema remains unchanged.
    op.execute(
        """
        UPDATE relationships
        SET relationship_type = lower(
            replace(replace(relationship_type, '-', '_'), ' ', '_')
        )
        """
    )


def downgrade() -> None:
    # Irreversible data normalization.
    pass
