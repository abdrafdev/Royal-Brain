"""day4 add sex to persons

Revision ID: 9b7c9bd6e7a5
Revises: 4e32f8f08df2
Create Date: 2026-01-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9b7c9bd6e7a5"
down_revision = "4e32f8f08df2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("persons", sa.Column("sex", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("persons", "sex")
