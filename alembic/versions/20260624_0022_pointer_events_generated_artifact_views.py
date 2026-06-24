"""Add pointer event policy foundation.

Revision ID: 20260624_0022
Revises: 20260624_0021
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260624_0022"
down_revision = "20260624_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_pointer_family_policies",
        sa.Column("artifact_pointer_family_policy_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("pointer_family", sa.String(length=128), nullable=False),
        sa.Column("registry_kind", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("basis_digest", sa.String(length=71), nullable=False),
        sa.Column("policy_digest", sa.String(length=71), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "artifact_pointer_family_policy_id",
            name="pk_artifact_pointer_family_policies",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_id",
            "pointer_family",
            name="uq_artifact_pointer_family_policies_scope_family",
        ),
    )
    op.create_index(
        "ix_artifact_pointer_family_policies_scope",
        "artifact_pointer_family_policies",
        ["tenant_id", "domain_id", "project_id", "state"],
        unique=False,
    )

    op.create_table(
        "artifact_pointer_events",
        sa.Column("artifact_pointer_event_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("pointer_id", sa.String(length=512), nullable=False),
        sa.Column("pointer_family", sa.String(length=128), nullable=False),
        sa.Column("event_kind", sa.String(length=64), nullable=False),
        sa.Column("from_generation", sa.Integer(), nullable=True),
        sa.Column("to_generation", sa.Integer(), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("previous_artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("basis_digest", sa.String(length=71), nullable=False),
        sa.Column("payload_digest", sa.String(length=71), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_actor_ref", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.ForeignKeyConstraint(["artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.ForeignKeyConstraint(
            ["previous_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.PrimaryKeyConstraint(
            "artifact_pointer_event_id",
            name="pk_artifact_pointer_events",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_id",
            "pointer_id",
            "event_kind",
            "to_generation",
            name="uq_artifact_pointer_events_generation",
        ),
    )
    op.create_index(
        "ix_artifact_pointer_events_scope",
        "artifact_pointer_events",
        ["tenant_id", "domain_id", "project_id", "pointer_family", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_artifact_pointer_events_pointer_generation",
        "artifact_pointer_events",
        ["pointer_id", "to_generation"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_artifact_pointer_events_pointer_generation",
        table_name="artifact_pointer_events",
    )
    op.drop_index(
        "ix_artifact_pointer_events_scope",
        table_name="artifact_pointer_events",
    )
    op.drop_table("artifact_pointer_events")

    op.drop_index(
        "ix_artifact_pointer_family_policies_scope",
        table_name="artifact_pointer_family_policies",
    )
    op.drop_table("artifact_pointer_family_policies")
