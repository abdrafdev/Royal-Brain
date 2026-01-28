"""day9_trust_and_certification_layer

Revision ID: 7a1ca4443bc2
Revises: e8f9a0b1c2d3
Create Date: 2026-01-15 16:54:45.613412

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a1ca4443bc2"
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    from sqlalchemy.engine import Connection
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Create entity_hashes table (cryptographic fingerprints)
    if "entity_hashes" not in existing_tables:
        op.create_table(
            "entity_hashes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False, index=True),
            sa.Column("entity_id", sa.Integer(), nullable=False, index=True),
            sa.Column("hash_algorithm", sa.String(32), nullable=False),
            sa.Column("hash_value", sa.String(128), nullable=False, index=True),
            sa.Column("canonical_json", sa.Text(), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("computed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("entity_type", "entity_id", "timestamp", name="uq_entity_hash_version"),
        )
        op.create_index("ix_entity_hashes_entity", "entity_hashes", ["entity_type", "entity_id"])
    
    # 2. Create verification_certificates table
    if "verification_certificates" not in existing_tables:
        op.create_table(
            "verification_certificates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False, index=True),
            sa.Column("entity_id", sa.Integer(), nullable=False, index=True),
            sa.Column("certificate_type", sa.String(64), nullable=False),
            sa.Column("verification_status", sa.String(32), nullable=False, index=True),
            sa.Column("hash_id", sa.Integer(), sa.ForeignKey("entity_hashes.id"), nullable=False),
            sa.Column("certificate_json", sa.JSON(), nullable=False),
            sa.Column("certificate_pdf_path", sa.String(512), nullable=True),
            sa.Column("sources_used", sa.JSON(), nullable=True),
            sa.Column("rules_applied", sa.JSON(), nullable=True),
            sa.Column("jurisdiction_id", sa.Integer(), sa.ForeignKey("jurisdictions.id"), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column("ai_explanation", sa.Text(), nullable=True),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("issued_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("signature", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_verification_certificates_entity", "verification_certificates", ["entity_type", "entity_id"])
    
    # 3. Create blockchain_anchors table (immutable proof)
    if "blockchain_anchors" not in existing_tables:
        op.create_table(
            "blockchain_anchors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("hash_id", sa.Integer(), sa.ForeignKey("entity_hashes.id"), nullable=True),
            sa.Column("merkle_root", sa.String(128), nullable=True),
            sa.Column("batch_id", sa.String(128), nullable=True, index=True),
            sa.Column("blockchain_network", sa.String(64), nullable=False),
            sa.Column("transaction_hash", sa.String(128), nullable=False, index=True),
            sa.Column("block_number", sa.Integer(), nullable=True),
            sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("anchor_type", sa.String(32), nullable=False),
            sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("anchored_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("explorer_url", sa.String(512), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_blockchain_anchors_batch", "blockchain_anchors", ["batch_id"])
    
    # 4. Extend audit_logs with hash tracking (if columns don't exist)
    audit_columns = [col["name"] for col in inspector.get_columns("audit_logs")]
    
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        if "hash_before" not in audit_columns:
            batch_op.add_column(sa.Column("hash_before", sa.String(128), nullable=True))
        if "hash_after" not in audit_columns:
            batch_op.add_column(sa.Column("hash_after", sa.String(128), nullable=True))
        if "verification_certificate_id" not in audit_columns:
            batch_op.add_column(sa.Column("verification_certificate_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_audit_logs_verification_certificate_id",
                "verification_certificates",
                ["verification_certificate_id"],
                ["id"],
            )


def downgrade() -> None:
    # Drop new columns from audit_logs
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_column("verification_certificate_id")
        batch_op.drop_column("hash_after")
        batch_op.drop_column("hash_before")
    
    # Drop new tables
    op.drop_table("blockchain_anchors")
    op.drop_table("verification_certificates")
    op.drop_table("entity_hashes")
