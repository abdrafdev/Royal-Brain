"""day7 orders legitimacy engine

Revision ID: d7e8f9a0b1c2
Revises: c6b9f0a1d2e3
Create Date: 2026-01-13

"""
from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "c6b9f0a1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Orders table extensions (idempotent)
    order_cols = {c["name"] for c in insp.get_columns("orders")}
    order_fks = insp.get_foreign_keys("orders")
    has_fons_fk = any(
        ("fons_honorum_person_id" in (fk.get("constrained_columns") or []))
        and fk.get("referred_table") == "persons"
        for fk in order_fks
    )
    has_founding_doc_fk = any(
        ("founding_document_source_id" in (fk.get("constrained_columns") or []))
        and fk.get("referred_table") == "sources"
        for fk in order_fks
    )
    has_grantor_fk = any(
        ("grantor_person_id" in (fk.get("constrained_columns") or []))
        and fk.get("referred_table") == "persons"
        for fk in order_fks
    )
    existing_order_indexes = {i["name"] for i in insp.get_indexes("orders")}

    with op.batch_alter_table("orders") as batch_op:
        # Classification and scoring fields
        if "classification" not in order_cols:
            batch_op.add_column(
                sa.Column(
                    "classification",
                    sa.String(length=32),
                    nullable=True,
                    comment="LEGITIMATE/SELF_STYLED/DISPUTED/FRAUDULENT",
                )
            )
        if "legitimacy_score" not in order_cols:
            batch_op.add_column(
                sa.Column(
                    "legitimacy_score",
                    sa.Integer(),
                    nullable=True,
                    comment="0-100 score based on validation factors",
                )
            )

        # Fons honorum (source of honor/authority)
        if "fons_honorum_person_id" not in order_cols:
            batch_op.add_column(
                sa.Column("fons_honorum_person_id", sa.Integer(), nullable=True)
            )
        if not has_fons_fk:
            batch_op.create_foreign_key(
                "fk_orders_fons_honorum_person_id",
                "persons",
                ["fons_honorum_person_id"],
                ["id"],
            )
        if "ix_orders_fons_honorum_person_id" not in existing_order_indexes:
            batch_op.create_index(
                "ix_orders_fons_honorum_person_id", ["fons_honorum_person_id"], unique=False
            )

        # Fraud detection fields
        if "fraud_flags" not in order_cols:
            batch_op.add_column(
                sa.Column(
                    "fraud_flags",
                    sa.JSON(),
                    nullable=True,
                    comment="List of fraud indicator strings",
                )
            )

        # Jurisdiction recognition
        if "recognized_by" not in order_cols:
            batch_op.add_column(
                sa.Column(
                    "recognized_by",
                    sa.JSON(),
                    nullable=True,
                    comment="List of jurisdiction codes that recognize this order",
                )
            )

        # Documentary evidence
        if "founding_document_source_id" not in order_cols:
            batch_op.add_column(
                sa.Column("founding_document_source_id", sa.Integer(), nullable=True)
            )
        if not has_founding_doc_fk:
            batch_op.create_foreign_key(
                "fk_orders_founding_document_source_id",
                "sources",
                ["founding_document_source_id"],
                ["id"],
            )
        if "ix_orders_founding_document_source_id" not in existing_order_indexes:
            batch_op.create_index(
                "ix_orders_founding_document_source_id",
                ["founding_document_source_id"],
                unique=False,
            )

        # Validation metadata
        if "last_legitimacy_check" not in order_cols:
            batch_op.add_column(
                sa.Column(
                    "last_legitimacy_check",
                    sa.DateTime(timezone=True),
                    nullable=True,
                    comment="Timestamp of most recent validation",
                )
            )

        # Grant metadata (for succession/continuity checks)
        if "granted_date" not in order_cols:
            batch_op.add_column(sa.Column("granted_date", sa.Date(), nullable=True))
        if "grantor_person_id" not in order_cols:
            batch_op.add_column(sa.Column("grantor_person_id", sa.Integer(), nullable=True))
        if not has_grantor_fk:
            batch_op.create_foreign_key(
                "fk_orders_grantor_person_id",
                "persons",
                ["grantor_person_id"],
                ["id"],
            )
        if "ix_orders_grantor_person_id" not in existing_order_indexes:
            batch_op.create_index(
                "ix_orders_grantor_person_id", ["grantor_person_id"], unique=False
            )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_grantor_person_id")
        batch_op.drop_constraint("fk_orders_grantor_person_id", type_="foreignkey")
        batch_op.drop_column("grantor_person_id")
        batch_op.drop_column("granted_date")

        batch_op.drop_column("last_legitimacy_check")

        batch_op.drop_index("ix_orders_founding_document_source_id")
        batch_op.drop_constraint("fk_orders_founding_document_source_id", type_="foreignkey")
        batch_op.drop_column("founding_document_source_id")

        batch_op.drop_column("recognized_by")
        batch_op.drop_column("fraud_flags")

        batch_op.drop_index("ix_orders_fons_honorum_person_id")
        batch_op.drop_constraint("fk_orders_fons_honorum_person_id", type_="foreignkey")
        batch_op.drop_column("fons_honorum_person_id")

        batch_op.drop_column("legitimacy_score")
        batch_op.drop_column("classification")
