"""Add explicit edge execution runtime state for logistics handoffs.

Revision ID: 20260307_0009
Revises: 20260307_0008
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0009"
down_revision = "20260307_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "edge_executions",
        sa.Column("edge_execution_id", sa.String(length=128), nullable=False),
        sa.Column("edge_id", sa.String(length=128), nullable=False),
        sa.Column("source_workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("source_stage_id", sa.String(length=128), nullable=False),
        sa.Column("source_artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("source_activation_key", sa.String(length=255), nullable=True),
        sa.Column("target_workflow_id", sa.String(length=128), nullable=False),
        sa.Column("target_workflow_run_id", sa.String(length=128), nullable=True),
        sa.Column("target_stage_id", sa.String(length=128), nullable=False),
        sa.Column("target_partition_kind", sa.String(length=64), nullable=False),
        sa.Column("target_partition_key", sa.String(length=255), nullable=False),
        sa.Column("target_activation_key", sa.String(length=255), nullable=True),
        sa.Column("correlation_key", sa.String(length=255), nullable=False),
        sa.Column("materialize_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("activation_idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cursor_state_json", sa.JSON(), nullable=True),
        sa.Column("compensation_state_json", sa.JSON(), nullable=True),
        sa.Column("input_bindings_json", sa.JSON(), nullable=True),
        sa.Column("trigger_ref", sa.String(length=255), nullable=True),
        sa.Column("seed_artifact_version_id", sa.String(length=128), nullable=True),
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
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["source_artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.ForeignKeyConstraint(["target_workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["seed_artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.PrimaryKeyConstraint("edge_execution_id", name="pk_edge_executions"),
        sa.UniqueConstraint(
            "edge_id",
            "source_workflow_run_id",
            "source_artifact_version_id",
            "target_partition_key",
            name="uq_edge_executions_scope",
        ),
        sa.UniqueConstraint(
            "edge_id",
            "correlation_key",
            name="uq_edge_executions_correlation",
        ),
    )

    op.create_index(
        "ix_edge_executions_source_scope",
        "edge_executions",
        ["source_workflow_run_id", "edge_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_edge_executions_target_scope",
        "edge_executions",
        ["target_workflow_run_id", "edge_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_edge_executions_target_scope", table_name="edge_executions")
    op.drop_index("ix_edge_executions_source_scope", table_name="edge_executions")
    op.drop_table("edge_executions")
