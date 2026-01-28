"""day6 jurisdiction engine fields

Revision ID: c6b9f0a1d2e3
Revises: 9b7c9bd6e7a5
Create Date: 2026-01-13

"""

from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c6b9f0a1d2e3"
down_revision = "9b7c9bd6e7a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Jurisdictions (idempotent)
    jur_cols = {c["name"] for c in insp.get_columns("jurisdictions")}

    if "code" not in jur_cols:
        op.add_column("jurisdictions", sa.Column("code", sa.String(length=8), nullable=True))
    if "legal_system" not in jur_cols:
        op.add_column(
            "jurisdictions", sa.Column("legal_system", sa.String(length=64), nullable=True)
        )
    if "nobility_abolished_date" not in jur_cols:
        op.add_column(
            "jurisdictions", sa.Column("nobility_abolished_date", sa.Date(), nullable=True)
        )
    if "succession_rules_json" not in jur_cols:
        op.add_column(
            "jurisdictions", sa.Column("succession_rules_json", sa.JSON(), nullable=True)
        )
    if "recognized_orders" not in jur_cols:
        op.add_column(
            "jurisdictions", sa.Column("recognized_orders", sa.JSON(), nullable=True)
        )
    if "legal_references" not in jur_cols:
        op.add_column(
            "jurisdictions", sa.Column("legal_references", sa.JSON(), nullable=True)
        )

    existing_jur_indexes = {i["name"] for i in insp.get_indexes("jurisdictions")}
    if "ix_jurisdictions_code" not in existing_jur_indexes:
        op.create_index("ix_jurisdictions_code", "jurisdictions", ["code"], unique=False)

    # Titles: grant metadata (SQLite requires batch mode for FK constraint changes)
    title_cols = {c["name"] for c in insp.get_columns("titles")}
    title_fks = insp.get_foreign_keys("titles")
    has_grantor_fk = any(
        ("grantor_person_id" in (fk.get("constrained_columns") or []))
        and fk.get("referred_table") == "persons"
        for fk in title_fks
    )
    existing_title_indexes = {i["name"] for i in insp.get_indexes("titles")}

    with op.batch_alter_table("titles") as batch_op:
        if "granted_date" not in title_cols:
            batch_op.add_column(sa.Column("granted_date", sa.Date(), nullable=True))
        if "grantor_person_id" not in title_cols:
            batch_op.add_column(sa.Column("grantor_person_id", sa.Integer(), nullable=True))
        if not has_grantor_fk:
            batch_op.create_foreign_key(
                "fk_titles_grantor_person_id",
                "persons",
                ["grantor_person_id"],
                ["id"],
            )
        if "ix_titles_grantor_person_id" not in existing_title_indexes:
            batch_op.create_index(
                "ix_titles_grantor_person_id", ["grantor_person_id"], unique=False
            )

    # Seed canonical jurisdictions (skip if already present).
    jurisdictions = sa.table(
        "jurisdictions",
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("legal_system", sa.String()),
        sa.column("nobility_abolished_date", sa.Date()),
        sa.column("succession_rules_json", sa.JSON()),
        sa.column("recognized_orders", sa.JSON()),
        sa.column("legal_references", sa.JSON()),
        sa.column("type", sa.String()),
        sa.column("notes", sa.Text()),
        sa.column("valid_from", sa.Date()),
        sa.column("valid_to", sa.Date()),
    )

    existing_codes = {
        r[0]
        for r in bind.execute(sa.text("SELECT code FROM jurisdictions WHERE code IS NOT NULL"))
        if r[0]
    }

    seed_rows = [
        {
            "name": "Italy",
            "code": "IT",
            "legal_system": "Civil Law",
            "nobility_abolished_date": date(1946, 6, 2),
            "succession_rules_json": {
                "title_recognition": {
                    "pre_abolition": "historic_recognition_only",
                    "post_abolition": "invalid",
                },
                "authority": [
                    "Ministry of Interior",
                    "Presidency of the Republic",
                ],
                "note": "Pre-1946 titles have historic recognition only; no legal privileges.",
            },
            "recognized_orders": [
                "Sovereign Military Order of Malta (SMOM)",
                "Holy See orders",
            ],
            "legal_references": [
                "Constitution Article 3",
                "Law March 3, 1951 n. 178",
            ],
            "type": "country",
            "notes": "Republic established 1946-06-02; nobility abolished.",
            "valid_from": date(1000, 1, 1),
            "valid_to": None,
        },
        {
            "name": "United Kingdom",
            "code": "GB",
            "legal_system": "Common Law",
            "nobility_abolished_date": None,
            "succession_rules_json": {
                "peerage_system": [
                    "Duke",
                    "Marquess",
                    "Earl",
                    "Viscount",
                    "Baron",
                ],
                "authority": ["Crown", "College of Arms"],
                "note": "Active peerage system; titles subject to Crown authority.",
            },
            "recognized_orders": [
                "Order of the Garter",
                "Order of the Thistle",
                "Order of the Bath",
                "Order of St Michael and St George",
            ],
            "legal_references": ["Royal Warrants", "Peerage Act 1963"],
            "type": "country",
            "notes": "Monarchy continues; peerage system active.",
            "valid_from": date(1000, 1, 1),
            "valid_to": None,
        },
        {
            "name": "Spain",
            "code": "ES",
            "legal_system": "Civil Law",
            "nobility_abolished_date": date(1931, 4, 14),
            "succession_rules_json": {
                "nobility_restored_date": "1978-12-27",
                "authority": ["Ministry of Justice", "Royal Household"],
                "note": "Titles require royal confirmation; Grandeza de España system.",
            },
            "recognized_orders": [
                "Order of the Golden Fleece",
                "Order of Charles III",
            ],
            "legal_references": ["Constitution 1978 Article 62"],
            "type": "country",
            "notes": "Nobility abolished 1931-04-14; monarchy restored 1978-12-27.",
            "valid_from": date(1000, 1, 1),
            "valid_to": None,
        },
        {
            "name": "United Arab Emirates",
            "code": "AE",
            "legal_system": "Islamic Law",
            "nobility_abolished_date": None,
            "succession_rules_json": {
                "note": "Consensus-based tribal succession; religious authority may be required.",
                "authority": [
                    "Federal Supreme Council",
                    "Individual Emirates rulers",
                ],
            },
            "recognized_orders": ["Order of Zayed", "Order of the Union"],
            "legal_references": ["UAE Constitution Article 51"],
            "type": "country",
            "notes": "Tribal/monarchical structures continue.",
            "valid_from": date(1000, 1, 1),
            "valid_to": None,
        },
    ]

    to_insert = [r for r in seed_rows if r["code"] not in existing_codes]
    if to_insert:
        op.bulk_insert(jurisdictions, to_insert)


def downgrade() -> None:
    op.drop_index("ix_titles_grantor_person_id", table_name="titles")
    op.drop_column("titles", "grantor_person_id")
    op.drop_column("titles", "granted_date")

    op.drop_index("ix_jurisdictions_code", table_name="jurisdictions")
    op.drop_column("jurisdictions", "legal_references")
    op.drop_column("jurisdictions", "recognized_orders")
    op.drop_column("jurisdictions", "succession_rules_json")
    op.drop_column("jurisdictions", "nobility_abolished_date")
    op.drop_column("jurisdictions", "legal_system")
    op.drop_column("jurisdictions", "code")
