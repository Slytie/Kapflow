"""Add CAPEX project anchors and direct memberships.

Revision ID: 20260604_0011
Revises: 20260313_0010
Create Date: 2026-06-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260604_0011"
down_revision = "20260313_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_projects",
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("project_id", name="pk_capex_projects"),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_key",
            name="uq_capex_projects_scope_key",
        ),
    )
    op.create_index(
        "ix_capex_projects_scope_lookup",
        "capex_projects",
        ["tenant_id", "domain_id", "state", "project_key"],
        unique=False,
    )

    op.create_table(
        "project_memberships",
        sa.Column("project_membership_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("granted_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("granted_by_actor_type", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("project_membership_id", name="pk_project_memberships"),
        sa.UniqueConstraint(
            "project_id",
            "actor_type",
            "actor_id",
            name="uq_project_memberships_actor",
        ),
    )
    op.create_index(
        "ix_project_memberships_actor_lookup",
        "project_memberships",
        ["tenant_id", "domain_id", "actor_type", "actor_id", "state"],
        unique=False,
    )

    op.add_column(
        "workflow_runs",
        sa.Column("project_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_workflow_runs_project_scope",
        "workflow_runs",
        ["tenant_id", "domain_id", "project_id"],
        unique=False,
    )

    op.add_column(
        "timeline_events",
        sa.Column("project_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_timeline_events_project_id",
        "timeline_events",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_events_project_id", table_name="timeline_events")
    op.drop_column("timeline_events", "project_id")
    op.drop_index("ix_workflow_runs_project_scope", table_name="workflow_runs")
    op.drop_column("workflow_runs", "project_id")
    op.drop_index("ix_project_memberships_actor_lookup", table_name="project_memberships")
    op.drop_table("project_memberships")
    op.drop_index("ix_capex_projects_scope_lookup", table_name="capex_projects")
    op.drop_table("capex_projects")
