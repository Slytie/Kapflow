"""Add CAPEX source occurrence and SourceRef runtime state.

Revision ID: 20260608_0013
Revises: 20260605_0012
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0013"
down_revision = "20260605_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_content_identities",
        sa.Column("content_identity_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("digest_algorithm", sa.String(length=32), nullable=False),
        sa.Column("content_digest", sa.String(length=255), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("media_type", sa.String(length=128), nullable=True),
        sa.Column("canonicalization_profile", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "content_identity_id",
            name="pk_capex_content_identities",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "digest_algorithm",
            "content_digest",
            name="uq_capex_content_identities_digest",
        ),
    )
    op.create_index(
        "ix_capex_content_identities_digest_lookup",
        "capex_content_identities",
        ["tenant_id", "domain_id", "digest_algorithm", "content_digest"],
        unique=False,
    )

    op.create_table(
        "capex_source_occurrences",
        sa.Column("source_occurrence_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("content_identity_id", sa.String(length=255), nullable=False),
        sa.Column("occurrence_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("locator_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("registered_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("registered_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["content_identity_id"],
            ["capex_content_identities.content_identity_id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "source_occurrence_id",
            name="pk_capex_source_occurrences",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "source_ref",
            name="uq_capex_source_occurrences_source_ref",
        ),
    )
    op.create_index(
        "ix_capex_source_occurrences_scope_status",
        "capex_source_occurrences",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_capex_source_occurrences_content_identity",
        "capex_source_occurrences",
        ["content_identity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_source_occurrences_content_identity",
        table_name="capex_source_occurrences",
    )
    op.drop_index(
        "ix_capex_source_occurrences_scope_status",
        table_name="capex_source_occurrences",
    )
    op.drop_table("capex_source_occurrences")
    op.drop_index(
        "ix_capex_content_identities_digest_lookup",
        table_name="capex_content_identities",
    )
    op.drop_table("capex_content_identities")
