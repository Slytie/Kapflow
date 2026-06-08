"""Add CAPEX closure governance runtime primitives.

Revision ID: 20260608_0014
Revises: 20260608_0013
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0014"
down_revision = "20260608_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_waivers",
        sa.Column("waiver_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("waiver_id", name="pk_capex_waivers"),
    )
    op.create_index(
        "ix_capex_waivers_scope_state",
        "capex_waivers",
        ["tenant_id", "domain_id", "project_id", "scope_kind", "scope_ref", "state"],
        unique=False,
    )

    op.create_table(
        "capex_closure_gate_evaluations",
        sa.Column("closure_gate_evaluation_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("closure_target_kind", sa.String(length=64), nullable=False),
        sa.Column("closure_target_ref", sa.String(length=255), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("required_dimensions_json", sa.JSON(), nullable=False),
        sa.Column("satisfied_dimensions_json", sa.JSON(), nullable=False),
        sa.Column("missing_dimensions_json", sa.JSON(), nullable=False),
        sa.Column("waiver_refs_json", sa.JSON(), nullable=False),
        sa.Column("basis_version_vector_json", sa.JSON(), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "closure_gate_evaluation_id",
            name="pk_capex_closure_gate_evaluations",
        ),
    )
    op.create_index(
        "ix_capex_closure_gate_evaluations_target",
        "capex_closure_gate_evaluations",
        [
            "tenant_id",
            "domain_id",
            "project_id",
            "closure_target_kind",
            "closure_target_ref",
            "result",
        ],
        unique=False,
    )

    op.create_table(
        "capex_closure_snapshots",
        sa.Column("closure_snapshot_id", sa.String(length=255), nullable=False),
        sa.Column("closure_gate_evaluation_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("closure_target_kind", sa.String(length=64), nullable=False),
        sa.Column("closure_target_ref", sa.String(length=255), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("basis_version_vector_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
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
            ["closure_gate_evaluation_id"],
            ["capex_closure_gate_evaluations.closure_gate_evaluation_id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "closure_snapshot_id",
            name="pk_capex_closure_snapshots",
        ),
    )
    op.create_index(
        "ix_capex_closure_snapshots_target_state",
        "capex_closure_snapshots",
        [
            "tenant_id",
            "domain_id",
            "project_id",
            "closure_target_kind",
            "closure_target_ref",
            "state",
        ],
        unique=False,
    )
    op.create_index(
        "ix_capex_closure_snapshots_evaluation",
        "capex_closure_snapshots",
        ["closure_gate_evaluation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_closure_snapshots_evaluation",
        table_name="capex_closure_snapshots",
    )
    op.drop_index(
        "ix_capex_closure_snapshots_target_state",
        table_name="capex_closure_snapshots",
    )
    op.drop_table("capex_closure_snapshots")
    op.drop_index(
        "ix_capex_closure_gate_evaluations_target",
        table_name="capex_closure_gate_evaluations",
    )
    op.drop_table("capex_closure_gate_evaluations")
    op.drop_index("ix_capex_waivers_scope_state", table_name="capex_waivers")
    op.drop_table("capex_waivers")
