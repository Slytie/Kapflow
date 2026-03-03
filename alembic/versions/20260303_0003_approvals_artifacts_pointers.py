"""Add approvals, artifact versions, and artifact pointers tables.

Revision ID: 20260303_0003
Revises: 20260303_0002
Create Date: 2026-03-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0003"
down_revision = "20260303_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("task_run_id", sa.String(length=128), nullable=True),
        sa.Column("approval_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("requested_by_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("candidate_roles", sa.JSON(), nullable=False),
        sa.Column("required_role", sa.String(length=128), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_kind", sa.String(length=64), nullable=True),
        sa.Column("response_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_actor_id", sa.String(length=128), nullable=True),
        sa.Column("decided_by_actor_type", sa.String(length=32), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.task_run_id"]),
        sa.ForeignKeyConstraint(["requested_by_task_run_id"], ["task_runs.task_run_id"]),
        sa.PrimaryKeyConstraint("approval_id", name="pk_approvals"),
    )
    op.create_index(
        "ix_approvals_workflow_state",
        "approvals",
        ["workflow_run_id", "state"],
        unique=False,
    )

    op.create_table(
        "artifact_versions",
        sa.Column("artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("task_run_id", sa.String(length=128), nullable=True),
        sa.Column("artifact_kind", sa.String(length=128), nullable=False),
        sa.Column("artifact_role", sa.String(length=64), nullable=True),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.String(length=255), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("parent_artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("supersedes_artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("lineage_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.task_run_id"]),
        sa.ForeignKeyConstraint(
            ["parent_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.PrimaryKeyConstraint("artifact_version_id", name="pk_artifact_versions"),
    )
    op.create_index(
        "ix_artifact_versions_workflow_kind",
        "artifact_versions",
        ["workflow_run_id", "artifact_kind", "created_at"],
        unique=False,
    )

    op.create_table(
        "artifact_pointers",
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("pointer_key", sa.String(length=255), nullable=False),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=False),
        sa.Column("artifact_kind", sa.String(length=128), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("promotion_reason", sa.String(length=255), nullable=True),
        sa.Column("promoted_by_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("approved_by_approval_id", sa.String(length=128), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.ForeignKeyConstraint(["promoted_by_task_run_id"], ["task_runs.task_run_id"]),
        sa.ForeignKeyConstraint(["approved_by_approval_id"], ["approvals.approval_id"]),
        sa.PrimaryKeyConstraint("workflow_run_id", "pointer_key", name="pk_artifact_pointers"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "artifact_kind",
            name="uq_artifact_pointers_scope",
        ),
    )
    op.create_index(
        "ix_artifact_pointers_workflow_scope",
        "artifact_pointers",
        ["workflow_run_id", "scope_kind", "scope_ref"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_pointers_workflow_scope", table_name="artifact_pointers")
    op.drop_table("artifact_pointers")
    op.drop_index("ix_artifact_versions_workflow_kind", table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index("ix_approvals_workflow_state", table_name="approvals")
    op.drop_table("approvals")
