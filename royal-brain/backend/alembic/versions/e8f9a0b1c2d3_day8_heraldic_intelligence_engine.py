"""day8_heraldic_intelligence_engine

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-01-14 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'e8f9a0b1c2d3'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist before adding them
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('heraldic_entities')}
    
    columns_to_add = [
        ('parsed_structure', sa.JSON),
        ('validation_status', sa.String(32)),
        ('validation_errors', sa.JSON),
        ('svg_cache', sa.Text),
        ('rule_violations', sa.JSON),
        ('jurisdiction_compliant', sa.Boolean),
        ('jurisdiction_compliance_detail', sa.Text),
        ('last_validation_check', sa.DateTime(timezone=True)),
        ('claimant_person_id', sa.Integer),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            op.add_column('heraldic_entities', sa.Column(col_name, col_type, nullable=True))
    
    # Create index if it doesn't exist
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('heraldic_entities')}
    if 'ix_heraldic_entities_claimant_person_id' not in existing_indexes:
        op.create_index('ix_heraldic_entities_claimant_person_id', 'heraldic_entities', ['claimant_person_id'], unique=False)


def downgrade() -> None:
    # Check what exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('heraldic_entities')}
    existing_columns = {col['name'] for col in inspector.get_columns('heraldic_entities')}
    
    # Drop index if exists
    if 'ix_heraldic_entities_claimant_person_id' in existing_indexes:
        op.drop_index('ix_heraldic_entities_claimant_person_id', table_name='heraldic_entities')
    
    # Drop columns if they exist
    columns_to_drop = [
        'claimant_person_id',
        'last_validation_check',
        'jurisdiction_compliance_detail',
        'jurisdiction_compliant',
        'rule_violations',
        'svg_cache',
        'validation_errors',
        'validation_status',
        'parsed_structure',
    ]
    
    for col_name in columns_to_drop:
        if col_name in existing_columns:
            op.drop_column('heraldic_entities', col_name)
